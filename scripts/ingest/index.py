"""
The inverted index.

Shape, chosen by measuring both options against the real corpus:

    unit-level postings (term -> doc, page, tf)   36.7 MB
    doc-level  postings (term -> doc, tf)          3.9 MB

Document-level postings win by 9.4x, and they turn out to be the better design
rather than merely the smaller one. Ranking needs no text at all, and page
numbers come from scanning the text of the handful of documents actually being
displayed - the same fetch that produces their snippets. The browser already
carries the tokeniser to parse queries, so that scan costs microseconds.

Layout written under `search/`:

    meta.json             corpus statistics and the shard directory
    manifest.json         one record per document, in posting-index order
    terms/<xx>.json       postings for every term starting with those 2 chars
    docs/<id>-<n>.json    document text, bucketed so no single fetch is huge

Terms are sharded on their first two characters, which keeps a typical shard at
a few KB and means a query touches only the handful it needs. It also makes
prefix expansion free: every term starting with "dy" already lives in one file,
so as-you-type completion needs no extra structure.
"""

import hashlib
import json
import math
from collections import Counter, defaultdict

import config

from . import tokens

# Text is split across files of roughly this size so that opening a 1,300-page
# textbook never means downloading it whole. Most documents are far smaller than
# this and occupy a single bucket regardless.
#
# The size is a direct lever on query cost: a result list showing three books
# fetches three buckets, so 200 KB buckets made one query a 612 KB download.
# 64 KB keeps that under 200 KB at the cost of roughly twice as many files.
BUCKET_BYTES = 64_000

# Two characters: ~350 B for a typical shard over this corpus. One character
# would mean ~108 KB per shard, and a four-word query would pull 400 KB for no
# benefit.
SHARD_WIDTH = 2

# Prefix frequency is wildly uneven - "co", "re" and "in" are an order of
# magnitude heavier than the rest - so any shard above this size is split one
# character deeper. The front end resolves a term by trying the longer key
# first, which costs it nothing and keeps every fetch small.
SHARD_SPLIT_BYTES = 24_000

# BM25 parameters. Defaults from the literature; exposed in meta.json so the
# front end scores exactly the way the build assumed.
BM25_K1 = 1.2
BM25_B = 0.75

# How much a match in the path, filename or title is worth relative to the body
# score. Scored as a separate field at query time (see search_cli.search), which
# is what makes 4thSem/DAA/Material/DP/ answer "DAA DP" when no page inside says
# either word, and what keeps a well-named 3-page note ahead of a textbook that
# merely mentions the topic 5,000 times.
PATH_FIELD_WEIGHT = 2.5

INDEX_VERSION = 1

# Windows refuses to open these as filenames whatever the extension, and git on
# Windows refuses to add or check out a path containing one. A shard keyed "con"
# therefore produces con.json, which `git add` rejects outright and which no
# Windows clone could ever receive. Such shards get a suffix, and meta.json
# carries the exceptions so the front end never has to know this list.
RESERVED_BASENAMES = (
    {"con", "prn", "aux", "nul"}
    | {f"com{n}" for n in range(10)}
    | {f"lpt{n}" for n in range(10)}
)


def shard_filename(key: str) -> str:
    """The on-disk name for a shard key, avoiding reserved device names."""
    return key + "_" if key in RESERVED_BASENAMES else key


def content_hash(path) -> str:
    """SHA-1 of a file's bytes, used to collapse duplicate documents."""
    digest = hashlib.sha1()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def find_duplicates(files, extracted) -> dict:
    """Map every duplicate path to the one path that will represent the group.

    Several textbooks live in both BOOKS/Course/ and a semester folder. Indexing
    both wastes space and, worse, puts two identical results in competition with
    each other at the top of the rankings.
    """
    by_hash = defaultdict(list)
    for rel, path in files:
        item = extracted.get(rel)
        if item is None or not item.has_text:
            continue
        by_hash[content_hash(path)].append(rel)

    canonical = {}
    for group in by_hash.values():
        if len(group) < 2:
            continue
        # Sorted order is arbitrary but stable, so rebuilds stay diff-clean.
        primary = sorted(group)[0]
        for rel in group:
            canonical[rel] = primary
    return canonical


def bucket_units(units) -> list:
    """Split a document's units into groups of about BUCKET_BYTES.

    Returns a list of (first_unit_index, [unit, ...]).
    """
    groups, current, start, size = [], [], 0, 0
    for offset, unit in enumerate(units):
        unit_size = len(unit.encode("utf-8"))
        if current and size + unit_size > BUCKET_BYTES:
            groups.append((start, current))
            current, start, size = [], offset, 0
        current.append(unit)
        size += unit_size
    if current:
        groups.append((start, current))
    return groups or [(0, [])]


def build(records, extracted, aliases):
    """Build postings and per-document statistics.

    `records` is the catalogue, already restricted to canonical documents and
    in the order that posting document indices refer to.
    """
    postings = defaultdict(list)     # term -> [[docIdx, tf, pathTf?], ...]
    doc_terms = {}                   # docId -> Counter, for TF-IDF keywords
    total_length = 0

    for doc_index, record in enumerate(records):
        item = extracted.get(record["path"])
        body = Counter()
        if item is not None:
            for unit in item.units:
                body.update(tokens.tokenize(unit))

        # Path terms come from every location this document is reachable at,
        # so a de-duplicated textbook stays findable under both of its folders.
        path_terms = Counter()
        for path in [record["path"]] + aliases.get(record["path"], []):
            path_terms.update(tokens.path_tokens(path))
        path_terms.update(tokens.tokenize(record["title"]))

        doc_terms[record["id"]] = body

        # Document length for BM25 normalisation counts body text only; path
        # terms are a handful of words and would skew short documents.
        length = sum(body.values())
        record["dl"] = length
        total_length += length

        for term in set(body) | set(path_terms):
            entry = [doc_index, body.get(term, 0)]
            if path_terms.get(term):
                entry.append(path_terms[term])
            postings[term].append(entry)

    doc_freq = {term: len(entries) for term, entries in postings.items()}
    avgdl = (total_length / len(records)) if records else 0.0

    return postings, doc_freq, doc_terms, avgdl


def shard_of(term: str) -> str:
    return term[:SHARD_WIDTH]


def write(out_dir, records, postings, avgdl, extracted, progress=True):
    """Write the whole index to disk, replacing anything already there."""
    terms_dir = out_dir / "terms"
    docs_dir = out_dir / "docs"
    for directory in (out_dir, terms_dir, docs_dir):
        directory.mkdir(parents=True, exist_ok=True)

    # A rebuild after files are renamed or removed must not leave orphans
    # behind, which would serve stale text and inflate the repo.
    removed = 0
    for stale in list(terms_dir.glob("*.json")) + list(docs_dir.glob("*.json")):
        stale.unlink()
        removed += 1

    shards = defaultdict(dict)
    for term, entries in postings.items():
        shards[shard_of(term)][term] = entries
    shards = _split_heavy_shards(shards)

    shard_files = {}
    for shard, mapping in shards.items():
        filename = shard_filename(shard)
        if filename != shard:
            shard_files[shard] = filename
        _dump(terms_dir / f"{filename}.json", dict(sorted(mapping.items())))

    # Document text, bucketed.
    text_files = 0
    for record in records:
        item = extracted.get(record["path"])
        if item is None or not item.has_text:
            record["buckets"] = 0
            continue
        groups = bucket_units(item.units)
        record["buckets"] = len(groups)
        for bucket_index, (first_unit, units) in enumerate(groups):
            _dump(docs_dir / f"{record['id']}-{bucket_index}.json",
                  {"id": record["id"], "from": first_unit, "units": units})
            text_files += 1

    _dump(out_dir / "manifest.json", records)
    _dump(out_dir / "meta.json", {
        "version": INDEX_VERSION,
        "docs": len(records),
        "avgdl": round(avgdl, 3),
        "k1": BM25_K1,
        "b": BM25_B,
        "pathWeight": PATH_FIELD_WEIGHT,
        "shardWidth": SHARD_WIDTH,
        # GitHub Pages serves an LFS file as its pointer, not its content, so
        # anything flagged lfs in the manifest has to be fetched from the media
        # host instead. generate_site.py does the same for the browse tree.
        "lfsBase": (f"https://media.githubusercontent.com/media/"
                    f"{config.GITHUB_OWNER}/{config.GITHUB_REPO}/"
                    f"{config.GITHUB_BRANCH}/"),
        "minTokenLen": tokens.MIN_TOKEN_LEN,
        "maxTokenLen": tokens.MAX_TOKEN_LEN,
        "bucketBytes": BUCKET_BYTES,
        # The front end needs to know which shards exist so a query for a term
        # in an empty prefix range does not fire a request that 404s.
        "shards": sorted(shards),
        # Only the shards whose file name differs from their key.
        "shardFiles": shard_files,
        "stopwords": sorted(tokens.STOPWORDS),
    })

    if progress:
        print(f"  removed {removed} stale file(s)")
        print(f"  wrote {len(shards)} term shard(s), {text_files} text file(s)")
    return {"shards": len(shards), "text_files": text_files}


def _split_heavy_shards(shards: dict) -> dict:
    """Re-shard oversized prefixes one character deeper, repeatedly.

    One pass is not enough: splitting "co" leaves "con" still heavy. This keeps
    going until every shard is under the limit or its key is as long as the
    terms in it.

    Terms exactly as long as their prefix have no deeper key and stay put, so
    "co" and "com" can both exist; the front end prefers the longest key present.
    """
    result = {}
    pending = dict(shards)

    while pending:
        nxt = {}
        for shard, mapping in pending.items():
            deeper = {term: entries for term, entries in mapping.items()
                      if len(term) > len(shard)}
            # Nothing left to split on, or already small enough.
            if _json_size(mapping) <= SHARD_SPLIT_BYTES or not deeper:
                result[shard] = mapping
                continue

            # Terms equal in length to the key cannot go deeper; keep them here.
            stay = {term: entries for term, entries in mapping.items()
                    if len(term) == len(shard)}
            if stay:
                result[shard] = stay
            for term, entries in deeper.items():
                nxt.setdefault(term[:len(shard) + 1], {})[term] = entries
        pending = nxt

    return result


def _json_size(payload) -> int:
    return len(json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
               .encode("utf-8"))


def _dump(path, payload) -> None:
    """Write compact JSON. Size matters more than readability here - every one
    of these files is downloaded by a browser and committed to the repo."""
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, separators=(",", ":"), ensure_ascii=False)
