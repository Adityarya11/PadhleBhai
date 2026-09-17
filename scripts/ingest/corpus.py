"""
Walking the corpus, and caching what extraction produced.

Extraction is the slow part of a build - a couple of minutes over 1.4 GB - and
almost nothing changes between runs. The cache keys each document on its path,
size and modification time, so a rebuild re-reads only what actually moved.
"""

import pickle
import sys
from pathlib import Path

import config

from . import extract

# Kept out of the published site and out of git: the leading dot means
# config.is_infrastructure() already skips it.
CACHE_DIR = config.ROOT / ".index-cache"
CACHE_FILE = CACHE_DIR / "extracted.pickle"
CACHE_VERSION = 1


def publishable_files() -> list:
    """Every file the site is allowed to index, as (rel, Path) pairs.

    Gated on exactly the same guards as generate_site.py. The index is a far
    worse leak path than the browse tree - full text in a greppable JSON file,
    permanent in git history - so this must never drift from the tree's rules.
    """
    found = []
    for path in sorted(config.ROOT.rglob("*")):
        if not path.is_file():
            continue
        rel = config.rel_posix(path)
        if any(config.is_infrastructure(part) for part in rel.split("/")):
            continue
        if config.is_private(rel) or config.is_unlisted(rel):
            continue
        found.append((rel, path))
    return found


def _signature(path: Path) -> tuple:
    try:
        stat = path.stat()
        return (stat.st_size, int(stat.st_mtime))
    except OSError:
        return (0, 0)


def _load_cache() -> dict:
    if not CACHE_FILE.exists():
        return {}
    try:
        with CACHE_FILE.open("rb") as handle:
            data = pickle.load(handle)
        if data.get("version") != CACHE_VERSION:
            return {}
        return data.get("entries", {})
    except Exception:
        # A corrupt or stale-format cache is never worth failing a build over.
        return {}


def _save_cache(entries: dict) -> None:
    CACHE_DIR.mkdir(exist_ok=True)
    with CACHE_FILE.open("wb") as handle:
        pickle.dump({"version": CACHE_VERSION, "entries": entries}, handle,
                    protocol=pickle.HIGHEST_PROTOCOL)


def extract_all(files, use_cache: bool = True, progress: bool = True) -> dict:
    """Extract every file, reusing cached results where nothing changed.

    Returns {rel: Extracted}.
    """
    cache = _load_cache() if use_cache else {}
    results, hits, misses = {}, 0, 0

    for index, (rel, path) in enumerate(files, 1):
        signature = _signature(path)
        cached = cache.get(rel)

        if cached and cached[0] == signature:
            results[rel] = cached[1]
            hits += 1
        else:
            if path.suffix.lower() in extract.EXTRACTABLE:
                results[rel] = extract.extract(path)
            else:
                results[rel] = extract.Extracted(error="unsupported extension")
            cache[rel] = (signature, results[rel])
            misses += 1

        if progress and index % 25 == 0:
            sys.stdout.write(f"\r  extracting {index}/{len(files)} ...")
            sys.stdout.flush()

    if progress:
        sys.stdout.write("\r" + " " * 46 + "\r")

    # Drop entries for files that no longer exist, so the cache cannot grow
    # without bound as material is renamed.
    present = {rel for rel, _ in files}
    _save_cache({rel: value for rel, value in cache.items() if rel in present})

    if progress:
        print(f"  extracted {len(results)} file(s): {hits} cached, {misses} read")
    return results
