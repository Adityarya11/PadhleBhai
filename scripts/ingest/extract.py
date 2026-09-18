"""
Per-page text extraction for every file type in the archive.

Every format is reduced to the same shape: an ordered list of text units, where
a unit is whatever a search result should be able to point at. For PDFs that is
a real page (so a hit can deep-link to `file.pdf#page=14`), for slide decks a
slide, and for formats with no native pagination a fixed-size chunk.

Only the standard library is used, apart from `pypdfium2` for PDFs. Office
formats are zip archives of XML, which is cheap to read directly and avoids
pulling in `python-docx` / `python-pptx` for what amounts to one regex each.
"""

import html
import json
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

# Formats without native pages are split into units of roughly this many
# characters, so a result still points at a specific part of a long file.
CHUNK_CHARS = 2000

# Extensions handled here. Anything else is catalogued but not searched.
PDF_EXTS = {".pdf"}
PPTX_EXTS = {".pptx", ".ppt"}
DOCX_EXTS = {".docx", ".doc"}
NOTEBOOK_EXTS = {".ipynb"}
PLAIN_EXTS = {".txt", ".py", ".cpp", ".c", ".h", ".md", ".json", ".yml", ".yaml"}

EXTRACTABLE = PDF_EXTS | PPTX_EXTS | DOCX_EXTS | NOTEBOOK_EXTS | PLAIN_EXTS


@dataclass
class Extracted:
    """The text of one document, split into addressable units."""

    units: list = field(default_factory=list)  # text per page/slide/chunk
    unit_name: str = "page"  # what a unit is called in the UI
    real_pages: int = 0  # native page count, 0 if n/a
    title: str = ""  # embedded title, if any
    error: str = ""  # why extraction failed, if it did

    @property
    def has_text(self) -> bool:
        return any(unit.strip() for unit in self.units)

    @property
    def char_count(self) -> int:
        return sum(len(unit) for unit in self.units)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _clean(text: str) -> str:
    """Collapse whitespace so that extracted text stays compact on disk."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t\f\v]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _xml_text(xml: str, tag: str, break_tag: str = "") -> str:
    """Pull the text out of every `<tag>` in an Office XML part.

    Office files store runs of text in many small elements, so the readable
    content is just those elements joined in document order. `break_tag` marks
    a boundary (a paragraph, say) that should become a newline.

    Text elements and break markers have to be matched in one pass: substituting
    breaks beforehand would insert newlines *between* the text elements, where a
    scan for `<tag>` can no longer see them, and every separate text box on a
    slide would then run into the next one.
    """
    # The tag name must be followed by '>' or whitespace-then-attributes.
    # A bare `[^>]*` would also match siblings that merely share a prefix -
    # <a:tab/>, <a:tableStyles>, <w:tbl>, <w:tc> - and the scan would then run
    # to the next real closing tag, dragging raw markup into the text.
    text_pattern = (
        r"<" + re.escape(tag) + r"(?:\s[^>]*)?>(.*?)</" + re.escape(tag) + r">"
    )
    if break_tag:
        pattern = text_pattern + r"|</" + re.escape(break_tag) + r">"
    else:
        pattern = text_pattern

    parts = []
    for match in re.finditer(pattern, xml, re.DOTALL):
        # group(1) is None when the alternation matched a break marker instead.
        parts.append(match.group(1) if match.group(1) is not None else "\n")
    return _clean(html.unescape("".join(parts)))


def _chunk(text: str, size: int = CHUNK_CHARS) -> list:
    """Split text into units of about `size` characters, on word boundaries."""
    text = _clean(text)
    if not text:
        return []
    if len(text) <= size:
        return [text]

    units, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            # Back up to the nearest whitespace so words are not cut in half.
            split = text.rfind(" ", start + size // 2, end)
            if split > start:
                end = split
        units.append(text[start:end].strip())
        start = end
    return [unit for unit in units if unit]


# ---------------------------------------------------------------------------
# Per-format extractors
# ---------------------------------------------------------------------------


def _extract_pdf(path: Path) -> Extracted:
    import pypdfium2 as pdfium

    doc = None
    try:
        doc = pdfium.PdfDocument(str(path))
        units = []
        for index in range(len(doc)):
            page = doc[index]
            textpage = page.get_textpage()
            try:
                units.append(_clean(textpage.get_text_range() or ""))
            finally:
                textpage.close()
                page.close()

        title = ""
        try:
            title = (doc.get_metadata_dict() or {}).get("Title", "") or ""
        except Exception:
            pass

        return Extracted(
            units=units, unit_name="page", real_pages=len(units), title=_clean(title)
        )
    except Exception as exc:
        return Extracted(error=f"{type(exc).__name__}: {exc}")
    finally:
        if doc is not None:
            try:
                doc.close()
            except Exception:
                pass


def _extract_pptx(path: Path) -> Extracted:
    try:
        with zipfile.ZipFile(path) as archive:
            slides = [
                name
                for name in archive.namelist()
                if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)
            ]
            # Zip order is arbitrary; slide numbers are what the reader sees.
            slides.sort(
                key=lambda name: int(
                    re.search(r"(\d+)", name.rsplit("/", 1)[1]).group(1)
                )
            )

            units = []
            for name in slides:
                xml = archive.read(name).decode("utf-8", "replace")
                # <a:t> holds every run of visible text, including speaker-facing
                # shapes; <a:p> is the paragraph boundary within a text box.
                units.append(_xml_text(xml, "a:t", break_tag="a:p"))

            title = ""
            if "docProps/core.xml" in archive.namelist():
                core = archive.read("docProps/core.xml").decode("utf-8", "replace")
                title = _xml_text(core, "dc:title")

            return Extracted(
                units=units, unit_name="slide", real_pages=len(units), title=title
            )
    except Exception as exc:
        return Extracted(error=f"{type(exc).__name__}: {exc}")


def _extract_docx(path: Path) -> Extracted:
    try:
        with zipfile.ZipFile(path) as archive:
            if "word/document.xml" not in archive.namelist():
                return Extracted(error="not a Word XML package")
            xml = archive.read("word/document.xml").decode("utf-8", "replace")
            text = _xml_text(xml, "w:t", break_tag="w:p")

            title = ""
            if "docProps/core.xml" in archive.namelist():
                core = archive.read("docProps/core.xml").decode("utf-8", "replace")
                title = _xml_text(core, "dc:title")

            # A .docx stores no page breaks of its own - pagination happens at
            # render time - so chunks are the honest unit here.
            return Extracted(units=_chunk(text), unit_name="section", title=title)
    except Exception as exc:
        return Extracted(error=f"{type(exc).__name__}: {exc}")


def _extract_notebook(path: Path) -> Extracted:
    try:
        notebook = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        parts = []
        for cell in notebook.get("cells", []):
            if cell.get("cell_type") not in ("markdown", "code"):
                continue
            source = cell.get("source", "")
            if isinstance(source, list):
                source = "".join(source)
            if source.strip():
                parts.append(source)
        # Outputs are deliberately skipped: they are mostly rendered tables and
        # tracebacks that add noise without helping anyone find the notebook.
        return Extracted(units=_chunk("\n\n".join(parts)), unit_name="cell block")
    except Exception as exc:
        return Extracted(error=f"{type(exc).__name__}: {exc}")


def _extract_plain(path: Path) -> Extracted:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        return Extracted(units=_chunk(text), unit_name="section")
    except Exception as exc:
        return Extracted(error=f"{type(exc).__name__}: {exc}")


_DISPATCH = [
    (PDF_EXTS, _extract_pdf),
    (PPTX_EXTS, _extract_pptx),
    (DOCX_EXTS, _extract_docx),
    (NOTEBOOK_EXTS, _extract_notebook),
    (PLAIN_EXTS, _extract_plain),
]


def extract(path) -> Extracted:
    """Extract addressable text units from one file.

    Never raises: a file that cannot be read comes back with `error` set and no
    units, so one bad document cannot abort a whole corpus build.
    """
    path = Path(path)
    ext = path.suffix.lower()
    for extensions, handler in _DISPATCH:
        if ext in extensions:
            return handler(path)
    return Extracted(error=f"unsupported extension {ext}")
