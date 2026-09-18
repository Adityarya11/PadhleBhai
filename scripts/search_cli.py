"""
Query the built index from the terminal.

    python scripts/search_cli.py dynamic programming
    python scripts/search_cli.py --limit 10 congestion control
    python scripts/search_cli.py --explain matrix chain

This is the reference implementation of retrieval. `assets/search.js` mirrors it
exactly - same tokeniser, same shard resolution, same BM25 - so this CLI is how
you check whether a ranking problem is in the index or in the browser.

It reads only what a browser would: meta.json, manifest.json, the shards the
query touches, and the text of the documents actually being shown.
"""

import argparse
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
from ingest import tokens

SEARCH_DIR = config.ROOT / "search"
SNIPPET_CHARS = 240


class Index:
    """Lazy reader over the built index, mimicking the browser's fetch pattern."""

    def __init__(self, root: Path = SEARCH_DIR):
        self.root = root
        self.meta = self._read("meta.json")
        self.docs = self._read("manifest.json")
        self.shard_keys = set(self.meta["shards"])
        self._shards = {}
        self.bytes_read = 0

    def _read(self, rel):
        path = self.root / rel
        data = path.read_bytes()
        self.bytes_read = getattr(self, "bytes_read", 0) + len(data)
        return json.loads(data.decode("utf-8"))

    def shard_for(self, term: str):
        """Resolve a term to its shard, preferring the longest key that exists.

        Shards are split deeper where a prefix is heavy, so "con" may live in
        con.json while "cat" lives in ca.json. Trying longest-first is what makes
        that transparent to the caller.
        """
        # A term shorter than the shard width has its whole self as the key, so
        # the floor is min(len(term), shardWidth) - not shardWidth. Getting this
        # wrong made range() empty for 1-character terms, and every digit query
        # ("lecture 5", "unit 3") silently matched nothing.
        floor = min(len(term), self.meta["shardWidth"])
        for length in range(len(term), floor - 1, -1):
            key = term[:length]
            if key in self.shard_keys:
                return self.load_shard(key)
        return {}

    def load_shard(self, key: str):
        if key not in self._shards:
            # A few shard keys collide with Windows device names, so the build
            # renames those files and records the mapping in meta.json.
            filename = self.meta.get("shardFiles", {}).get(key, key)
            self._shards[key] = self._read(f"terms/{filename}.json")
        return self._shards[key]

    def postings(self, term: str):
        return self.shard_for(term).get(term, [])

    def expand_prefix(self, prefix: str, limit: int = 24):
        """Every indexed term starting with `prefix`, for as-you-type matching."""
        shard = self.shard_for(prefix)
        return sorted(t for t in shard if t.startswith(prefix))[:limit]

    def doc_text(self, record, bucket: int = 0):
        if not record.get("buckets"):
            return None
        return self._read(f"docs/{record['id']}-{bucket}.json")


def idf(total_docs: int, doc_freq: int) -> float:
    return math.log(1 + (total_docs - doc_freq + 0.5) / (doc_freq + 0.5))


def search(index: Index, query: str, limit: int = 8, prefix_last: bool = True):
    """Rank documents for a query. Returns (results, matched_terms)."""
    query_terms = tokens.tokenize(query)
    if not query_terms:
        return [], []

    total = index.meta["docs"]
    k1, b = index.meta["k1"], index.meta["b"]
    avgdl = index.meta["avgdl"] or 1.0
    path_weight = index.meta["pathWeight"]

    body_scores, path_scores = {}, {}
    covered = {}  # doc -> query positions matched at all
    path_covered = {}  # doc -> query positions matched in the name/path
    matched = []

    for position, term in enumerate(query_terms):
        is_last = position == len(query_terms) - 1
        # Only the final term gets prefix-expanded, so typing "dynam" finds
        # "dynamic" without "dp" also matching every term starting with "dp".
        variants = [term]
        if prefix_last and is_last and len(term) >= 3:
            variants = index.expand_prefix(term) or [term]

        for variant in variants:
            entries = index.postings(variant)
            if not entries:
                continue
            matched.append(variant)

            body_idf = idf(total, len(entries))
            # The path field needs its own IDF. "5" occurs in nearly every
            # document's body, so its body IDF is ~0 - but only a handful of
            # files are *named* "..._5_...", which makes it highly selective
            # there. Counting path-bearing entries costs nothing: the postings
            # are already in hand.
            path_df = sum(1 for e in entries if len(e) > 2 and e[2])
            path_idf = idf(total, path_df) if path_df else 0.0

            # An expanded variant should not outrank the term actually typed.
            damp = 1.0 if variant == term else 0.35

            for entry in entries:
                doc_index, body_tf = entry[0], entry[1]
                path_tf = entry[2] if len(entry) > 2 else 0

                if body_tf > 0:
                    dl = index.docs[doc_index].get("dl", 0)
                    norm = k1 * (1 - b + b * (dl / avgdl))
                    body_scores[doc_index] = body_scores.get(doc_index, 0.0) + (
                        body_idf * (body_tf * (k1 + 1)) / (body_tf + norm) * damp
                    )
                    covered.setdefault(doc_index, set()).add(position)

                # Path and title: its own field, saturating but not
                # length-normalised - that field is a fixed handful of words for
                # every document. Folded into body_tf instead, it vanished on
                # long ones, and a 1,312-page textbook outranked the 3-page note
                # actually titled "Matrix Chain Multiplication".
                if path_tf > 0:
                    path_scores[doc_index] = path_scores.get(doc_index, 0.0) + (
                        path_idf
                        * path_weight
                        * (path_tf * (k1 + 1))
                        / (path_tf + k1)
                        * damp
                    )
                    covered.setdefault(doc_index, set()).add(position)
                    path_covered.setdefault(doc_index, set()).add(position)

    scores = {}
    for doc_index in set(body_scores) | set(path_scores):
        # A name match is only compelling when the whole query matches the name.
        # "CUDA-Programming-Parallel.pdf" should not win "dynamic programming"
        # on the strength of one word in its title.
        path_fraction = len(path_covered.get(doc_index, ())) / len(query_terms)
        total_score = (
            body_scores.get(doc_index, 0.0)
            + path_scores.get(doc_index, 0.0) * path_fraction
        )

        # Coverage: matching every word beats matching one common word loudly.
        coverage = len(covered.get(doc_index, ())) / len(query_terms)
        scores[doc_index] = total_score * coverage**1.5

    ranked = sorted(scores.items(), key=lambda kv: -kv[1])[:limit]
    results = [{"doc": index.docs[i], "score": s} for i, s in ranked]
    return results, sorted(set(matched))


def locate(
    index: Index,
    record,
    query_terms,
    max_hits: int = 3,
    max_buckets: int = 1,
    start_bucket: int = 0,
):
    """Find which units of a document contain the query terms.

    Ranking never needs this - it runs only for the results actually on screen,
    which is why the index stores no unit-level postings at all.

    `max_buckets` caps how much text is pulled. It defaults to one because 92%
    of documents fit in a single bucket, while a textbook can span 29 of them:
    scanning all of those to find a snippet turned one query into a 999 KB
    download. For the rest, the caller asks for more buckets on demand.

    Returns (hits, scanned_all).
    """
    if not record.get("buckets"):
        return [], True

    wanted = set(query_terms)
    hits = []
    last = min(record["buckets"], start_bucket + max_buckets)

    for bucket in range(start_bucket, last):
        payload = index.doc_text(record, bucket)
        if not payload:
            continue
        for offset, unit in enumerate(payload["units"]):
            overlap = wanted & set(tokens.tokenize(unit))
            if not overlap:
                continue
            hits.append(
                {
                    "unit": payload["from"] + offset,
                    "terms": sorted(overlap),
                    "snippet": snippet(unit, overlap),
                }
            )
            if len(hits) >= max_hits:
                return hits, last >= record["buckets"]

    return hits, last >= record["buckets"]


def snippet(text: str, terms) -> str:
    """A window of text centred on the first matching term."""
    lowered = text.lower()
    position = -1
    for term in terms:
        found = lowered.find(term)
        if found >= 0 and (position < 0 or found < position):
            position = found
    if position < 0:
        position = 0

    start = max(0, position - SNIPPET_CHARS // 3)
    excerpt = text[start : start + SNIPPET_CHARS].replace("\n", " ")
    excerpt = re.sub(r"\s+", " ", excerpt).strip()
    return ("..." if start > 0 else "") + excerpt + "..."


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", nargs="+")
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument(
        "--deep",
        type=int,
        default=0,
        metavar="N",
        help="scan up to N text buckets per result for snippets "
        "(default 1; large books span many)",
    )
    parser.add_argument(
        "--explain",
        action="store_true",
        help="show scores, matched terms and bytes fetched",
    )
    args = parser.parse_args()

    if not (SEARCH_DIR / "meta.json").exists():
        print("No index found. Run: python scripts/build_index.py")
        return 1

    index = Index()
    query = " ".join(args.query)
    results, matched = search(index, query, args.limit)

    if not results:
        print(f"No matches for {query!r}")
        return 0

    query_terms = tokens.tokenize(query)
    if args.explain:
        print(f"query terms: {query_terms}")
        print(f"matched index terms: {matched}")
        print()

    for rank, item in enumerate(results, 1):
        doc = item["doc"]
        label = f"{doc['sem']}/{doc['subject']}".strip("/") or doc["path"].split("/")[0]
        score = f"  [{item['score']:.2f}]" if args.explain else ""
        flag = "" if doc["text"] else "   (no text layer - matched on name/path)"
        print(f"{rank}. {doc['title']}{score}{flag}")
        print(f"   {doc['path']}")
        meta = [label, doc["category"]]
        if doc["pages"]:
            meta.append(f"{doc['pages']} {doc['unit']}s")
        print(f"   {' | '.join(m for m in meta if m)}")
        if doc.get("also_at"):
            print(f"   also at: {', '.join(doc['also_at'])}")
        if doc.get("keywords"):
            print(f"   keywords: {', '.join(doc['keywords'][:6])}")

        hits, complete = locate(
            index, doc, query_terms, max_buckets=args.deep if args.deep else 1
        )
        for hit in hits:
            print(f"   -> {doc['unit']} {hit['unit'] + 1}: {hit['snippet'][:150]}")
        if not hits and not complete:
            remaining = doc["buckets"] - 1
            print(
                f"   -> matches deeper in the document "
                f"({remaining} more section(s); --deep {doc['buckets']} to scan)"
            )
        print()

    if args.explain:
        print(f"fetched {index.bytes_read / 1024:.0f} KB to answer this query")
    return 0


if __name__ == "__main__":
    sys.exit(main())
