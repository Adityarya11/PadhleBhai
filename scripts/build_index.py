"""
Build the search index.

    python scripts/build_index.py              # incremental, uses the cache
    python scripts/build_index.py --no-cache   # re-read every file
    python scripts/build_index.py --stats      # report only, write nothing

Reads every publishable file, extracts its text, and writes `search/` - the
catalogue, the term shards and the per-document text the front end fetches for
snippets. Guarded material is excluded at the walk, not filtered out later.
"""

import argparse
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
from ingest import catalogue, corpus, tokens
from ingest import index as index_mod

OUT_DIR = config.ROOT / "search"


def human(num_bytes: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if num_bytes < 1024 or unit == "GB":
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024


def directory_size(path: Path) -> int:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def lfs_paths() -> set:
    import subprocess

    try:
        result = subprocess.run(
            ["git", "-c", "core.quotepath=off", "lfs", "ls-files", "--name-only"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="surrogateescape",
            cwd=config.ROOT,
        )
        return {line.strip() for line in result.stdout.splitlines() if line.strip()}
    except Exception:
        return set()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="ignore the extraction cache and re-read every file",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="report what would be built without writing anything",
    )
    args = parser.parse_args()

    started = time.time()
    print(f"Indexing {config.ROOT}")

    files = corpus.publishable_files()
    print(f"  {len(files)} publishable file(s)")

    extracted = corpus.extract_all(files, use_cache=not args.no_cache)

    # --- collapse duplicates -------------------------------------------------
    canonical = index_mod.find_duplicates(files, extracted)
    aliases = {}
    for rel, primary in canonical.items():
        if rel != primary:
            aliases.setdefault(primary, []).append(rel)
    if aliases:
        duplicate_count = sum(len(v) for v in aliases.values())
        print(
            f"  {duplicate_count} duplicate copy/copies folded into "
            f"{len(aliases)} document(s)"
        )

    # --- catalogue -----------------------------------------------------------
    lfs = lfs_paths()
    records, indexed, skipped = [], 0, 0
    for rel, path in files:
        if canonical.get(rel, rel) != rel:
            continue  # a duplicate of something else
        item = extracted[rel]
        record = catalogue.make_record(rel, path, item, lfs)
        record["also_at"] = sorted(aliases.get(rel, []))
        records.append(record)
        if item.has_text:
            indexed += 1
        else:
            skipped += 1

    print(
        f"  {len(records)} catalogue record(s): "
        f"{indexed} with text, {skipped} by name only"
    )

    # --- index ---------------------------------------------------------------
    postings, doc_freq, doc_terms, avgdl = index_mod.build(records, extracted, aliases)
    catalogue.add_keywords(records, doc_terms, doc_freq, len(records))

    print(
        f"  {len(postings):,} term(s), "
        f"{sum(len(v) for v in postings.values()):,} posting(s), avgdl {avgdl:.0f}"
    )

    if args.stats:
        print(f"\nNothing written (--stats). {time.time() - started:.0f}s")
        return 0

    # --- safety net ----------------------------------------------------------
    # The index is a worse leak path than the browse tree: full text, greppable,
    # permanent in history. Re-check every record rather than trusting the walk.
    leaked = [
        r["path"]
        for r in records
        if config.is_private(r["path"]) or config.is_unlisted(r["path"])
    ]
    if leaked:
        print(f"\nABORTED: {len(leaked)} guarded path(s) reached the index:")
        for path in leaked[:10]:
            print(f"   {path}")
        return 1

    index_mod.write(OUT_DIR, records, postings, avgdl, extracted)

    total = directory_size(OUT_DIR)
    terms = directory_size(OUT_DIR / "terms")
    docs = directory_size(OUT_DIR / "docs")
    manifest = (OUT_DIR / "manifest.json").stat().st_size

    print()
    print(f"  manifest  {human(manifest):>10}")
    print(f"  terms     {human(terms):>10}")
    print(f"  docs      {human(docs):>10}")
    print(f"  total     {human(total):>10}")
    print(f"\nBuilt in {time.time() - started:.0f}s -> {OUT_DIR.name}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
