"""
One metadata record per document.

The catalogue is what the `@` picker searches, what the browse UI renders, and
what a result card is built from. It is small enough (a few hundred entries) to
ship to the browser whole and query with no network round trip.
"""

import hashlib
import re

from . import tokens

# A path segment matching one of these words classifies the document. Checked in
# order, most specific first, against every segment of the path.
CATEGORY_RULES = [
    ("book", {"books", "book"}),
    ("paper", {"research", "papers", "paper"}),
    ("lab", {"lab", "labs", "practical", "practicals"}),
    ("assignment", {"assign", "assignment", "assignments", "tut", "tute", "tutorial", "ass"}),
    ("lecture", {"lecture", "lectures", "slides", "slide"}),
    ("notes", {"notes", "note"}),
    ("material", {"material", "materials"}),
]

SEMESTER_RE = re.compile(r"^(\d+)(?:st|nd|rd|th)Sem$", re.IGNORECASE)

# Leading numbering on a filename ("07_", "Lecture 3 - ") carries ordering, not
# meaning, so it is trimmed when deriving a display title.
LEADING_NUMBER_RE = re.compile(r"^\d+[\s._-]+")


def doc_id(rel: str) -> str:
    """Short stable identifier for a path.

    Derived from the path so that a rebuild produces the same ids and the diff
    stays readable; 10 hex characters is ample for a few hundred documents.
    """
    return hashlib.sha1(rel.encode("utf-8")).hexdigest()[:10]


def title_from_name(name: str) -> str:
    """Turn a filename into something readable enough to show as a heading."""
    stem = name.rsplit(".", 1)[0]
    stem = stem.replace("_", " ").replace("-", " ")
    stem = LEADING_NUMBER_RE.sub("", stem)
    stem = re.sub(r"\s+", " ", stem).strip()
    return stem or name


def classify(rel: str) -> str:
    """Infer what kind of material this is from where it sits."""
    segments = {segment.lower() for segment in rel.split("/")[:-1]}
    # The filename counts too: "Lecture_2.pdf" sitting loose in a subject folder
    # is still a lecture.
    name_words = set(tokens.tokenize(rel.rsplit("/", 1)[-1]))

    for category, keywords in CATEGORY_RULES:
        if segments & keywords or name_words & keywords:
            return category
    return "other"


def semester_of(rel: str) -> str:
    """The semester folder a document lives under, or '' for BOOKS and friends."""
    top = rel.split("/")[0]
    return top if SEMESTER_RE.match(top) else ""


def subject_of(rel: str) -> str:
    """The course folder, when the path is deep enough to have one."""
    parts = rel.split("/")
    # parts[0] is the semester or top-level group; a subject only exists if
    # there is at least one directory between that and the file itself.
    return parts[1] if len(parts) > 2 else ""


def make_record(rel: str, path, extracted, lfs_paths=frozenset()) -> dict:
    """Build the catalogue entry for one document."""
    name = rel.rsplit("/", 1)[-1]
    ext = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""

    try:
        size = path.stat().st_size
    except OSError:
        size = 0

    title = (extracted.title or "").strip()
    # Producers leave junk in the Title field - "PowerPoint Presentation",
    # "Microsoft Word - foo.doc" - which is worse than the filename.
    if (not title or len(title) < 4 or title.lower().startswith(
            ("powerpoint present", "microsoft word", "untitled", "slide "))):
        title = title_from_name(name)

    return {
        "id": doc_id(rel),
        "path": rel,
        "name": name,
        "title": title,
        "sem": semester_of(rel),
        "subject": subject_of(rel),
        "category": classify(rel),
        "ext": ext,
        "size": size,
        "units": len(extracted.units),
        "unit": extracted.unit_name,
        "pages": extracted.real_pages,
        "text": bool(extracted.has_text),
        "lfs": rel in lfs_paths,
        "keywords": [],          # filled in once corpus-wide IDF is known
    }


def add_keywords(records, doc_terms, doc_freq, total_docs, limit=8):
    """Attach the most distinctive terms of each document, by TF-IDF.

    This is what lets a document card read usefully without an LLM: the terms a
    document uses far more than the rest of the corpus does are, in practice, a
    decent summary of what it covers.
    """
    import math

    for record in records:
        counts = doc_terms.get(record["id"])
        if not counts:
            continue

        longest = max(counts.values())
        scored = []
        for term, count in counts.items():
            if term.isdigit():
                continue          # page numbers and years are not topics
            tf = count / longest
            idf = math.log((total_docs + 1) / (doc_freq.get(term, 0) + 1))
            scored.append((tf * idf, term))

        scored.sort(reverse=True)
        record["keywords"] = [term for _, term in scored[:limit]]
