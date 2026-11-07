import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
import pypdfium2 as pdfium

from ingest import catalogue, extract

CHUNK_SCHEMA_VERSION = 1
CHUNKS_FILE = config.ROOT / "search" / "chunks.jsonl"
PREVIEW_FILE = config.ROOT / ".index-cache" / "chunks.preview.jsonl"

DEFAULT_PDF = "BOOKS/Course/Silberschatz-Gagne-OS-Concepts.pdf"
MAX_CHUNKS_CHARS = 2000
OVERLAP_CHARS = 200

SKIP_TITLES = {
    "cover",
    "title page",
    "copyright",
    "contents",
    "brief contents",
    "table of contents",
    "index",
    "dedication",
}


def get_sections(path):
    doc = pdfium.PdfDocument(path)
    try:
        total = len(doc)
        toc = list(doc.get_toc())

        sections = []
        for entry in toc:
            dest = entry.get_dest()
            start = dest.get_index() if dest else None
            if start is None:
                continue
            sections.append(
                {
                    "title": (entry.get_title() or "").strip() or "(untitled)",
                    "level": entry.level + 1,
                    "start_page": start,
                    "end_page": total - 1,
                }
            )

        open_stack = []
        for index, section in enumerate(sections):
            while open_stack and section["level"] <= sections[open_stack[-1]]["level"]:
                closed = sections[open_stack.pop()]
                closed["end_page"] = max(
                    closed["start_page"], section["start_page"] - 1
                )
            open_stack.append(index)

        for index in open_stack:
            sections[index]["end_page"] = total - 1

        return sections, total
    finally:
        doc.close()


def add_breadcrumbs(sections, book):
    stack = []
    for section in sections:
        while stack and section["level"] <= stack[-1]["level"]:
            stack.pop()
        stack.append(section)
        section["breadcrumb"] = " > ".join([book] + [s["title"] for s in stack])


def own_pages(sections):
    """Pages each section keeps, after its descendants have taken theirs.

    A page goes to the deepest sections covering it. Siblings at that depth all
    keep it - outline entries legitimately share a page - but every ancestor
    gives it up, which is what stops the same text being chunked once per level.
    """
    deepest = {}
    for section in sections:
        for page in range(section["start_page"], section["end_page"] + 1):
            if page not in deepest or section["level"] > deepest[page]:
                deepest[page] = section["level"]

    pages = [[] for _ in sections]
    for index, section in enumerate(sections):
        for page in range(section["start_page"], section["end_page"] + 1):
            if deepest[page] == section["level"]:
                pages[index].append(page)
    return pages


def section_text(units, pages):
    pieces, offsets, cursor = [], [], 0
    for page in pages:
        if page >= len(units):
            continue
        text = units[page].strip()
        if not text:
            continue
        if pieces:
            cursor += 2
        offsets.append((page, cursor))
        pieces.append(text)
        cursor += len(text)
    return "\n\n".join(pieces), offsets


def page_at(offsets, position):
    page = offsets[0][0]
    for candidate, start in offsets:
        if start <= position:
            page = candidate
        else:
            break
    return page


def passage_spans(text, size=MAX_CHUNKS_CHARS, overlap=OVERLAP_CHARS):
    if not text.strip():
        return []
    overlap = min(overlap, size // 4)
    spans, start, length = [], 0, len(text)
    while start < length:
        end = min(start + size, length)
        if end < length:
            cut = text.rfind("\n\n", start + size // 2, end)
            if cut == -1:
                cut = text.rfind(" ", start + size // 2, end)
            if cut > start:
                end = cut
        spans.append((start, end))
        if end >= length:
            break
        start = max(end - overlap, start + 1)
    return spans


def title_of(rel):
    return Path(rel).stem.replace("_", " ").replace("-", " ")


def indexed_text(breadcrumb, text):
    return f"{breadcrumb}\n\n{text}"


def make_chunks(rel, item, sections, pages):
    doc_id = catalogue.doc_id(rel)
    units = item.units

    chunks = []
    for section, section_pages in zip(sections, pages):
        if not section_pages:
            continue
        if section["title"].strip().lower() in SKIP_TITLES:
            continue
        text, offsets = section_text(units, section_pages)
        if not text.strip():
            continue
        for start, end in passage_spans(text):
            body = text[start:end].strip()
            if not body:
                continue
            breadcrumb = section["breadcrumb"]
            chunks.append(
                {
                    "schema_version": CHUNK_SCHEMA_VERSION,
                    "id": f"{doc_id}-{len(chunks):04d}",
                    "doc_id": doc_id,
                    "path": rel,
                    "breadcrumb": breadcrumb,
                    "level": section["level"],
                    "page_start": page_at(offsets, start),
                    "page_end": page_at(offsets, end - 1),
                    "text": body,
                    "content_hash": hashlib.sha1(
                        indexed_text(breadcrumb, body).encode("utf-8")
                    ).hexdigest(),
                }
            )
    return chunks


def write_jsonl(records, out_file):
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with out_file.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
            handle.write("\n")


def preview(path):
    rel = config.rel_posix(Path(path))
    item = extract.extract(path)
    sections, _total = get_sections(path)
    add_breadcrumbs(sections, title_of(rel))

    pages = own_pages(sections)
    chunks = make_chunks(rel, item, sections, pages)

    print(f"{len(item.units)} pages of text")
    print(f"{len(sections)} sections, {sum(1 for p in pages if not p)} keep no pages")
    print(f"{len(chunks)} chunks, {sum(len(c['text']) for c in chunks):,} chars\n")

    write_jsonl(chunks, PREVIEW_FILE)
    lines = PREVIEW_FILE.read_text(encoding="utf-8").splitlines()
    print(f"{PREVIEW_FILE.name}: {len(lines)} line(s), first reads back clean")
    print(json.dumps(json.loads(lines[0]), indent=2, ensure_ascii=False)[:800])
    print()

    for chunk in chunks[:3]:
        print(
            f"p{chunk['page_start'] + 1}-{chunk['page_end'] + 1}  {chunk['breadcrumb']}"
        )
        print(f"   {chunk['text'][:100]!r}\n")


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PDF
    preview(path)


if __name__ == "__main__":
    main()
