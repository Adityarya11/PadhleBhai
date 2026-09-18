"""
Keep the repository honest about what it publishes.

Checks performed:
  1. .gitignore contains an up-to-date managed block for config.PRIVATE.
  2. No private file is still tracked by git (a .gitignore rule does not untrack
     a file that was committed before the rule existed).
  3. No tracked file is missing from disk (stale index entries).
  4. No file above the GitHub size limit is tracked outside Git LFS.
  5. No empty directories are left behind after a cleanup.
  6. The search index matches the corpus, and leaks nothing guarded into it.

Usage:
    python scripts/guard.py          # report only, exit 1 if anything is wrong
    python scripts/guard.py --fix    # rewrite the managed block, untrack files
                                     # (`git rm --cached` never deletes your
                                     #  local copies; changes are left staged)
"""

import argparse
import subprocess
import sys
from pathlib import Path

import config

BLOCK_START = (
    "# >>> managed by scripts/guard.py - edit PRIVATE in scripts/config.py >>>"
)
BLOCK_END = "# <<< managed by scripts/guard.py <<<"


def git(*args, check: bool = False) -> subprocess.CompletedProcess:
    """Run git at the repo root.

    `core.quotepath=off` plus an explicit UTF-8 decode keeps non-ASCII file
    names intact; without both, git escapes them and Python decodes the result
    with the platform locale, which turns real paths into unreadable ones.
    """
    return subprocess.run(
        ["git", "-c", "core.quotepath=off", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="surrogateescape",
        cwd=config.ROOT,
        check=check,
    )


def tracked_files() -> list:
    out = git("ls-files", "-z").stdout
    return [p for p in out.split("\0") if p]


def lfs_files() -> set:
    try:
        out = git("lfs", "ls-files", "--name-only").stdout
        return {line.strip() for line in out.splitlines() if line.strip()}
    except Exception:
        return set()


# ---------------------------------------------------------------------------
# 1. .gitignore managed block
# ---------------------------------------------------------------------------


def gitignore_lines() -> list:
    """Translate config.PRIVATE patterns into .gitignore rules."""
    lines = []
    for pattern in config.PRIVATE:
        pattern = pattern.rstrip("/")
        if "/" in pattern:
            # git anchors any pattern containing a slash to the repo root, so
            # mirror that explicitly and mark directories with a trailing slash.
            line = pattern if pattern.startswith("/") else "/" + pattern
            if (config.ROOT / pattern.lstrip("/")).is_dir():
                line += "/"
        else:
            # A pattern with no slash matches that name at any depth in git.
            # Leaving it unanchored is what makes "__pycache__" and "*_LAB"
            # cover nested folders rather than only ones at the repo root.
            line = pattern
        lines.append(line)
    return lines


def split_gitignore(text: str):
    """Return (before, after) around the managed block, dropping the old block."""
    if BLOCK_START in text and BLOCK_END in text:
        before, rest = text.split(BLOCK_START, 1)
        _, after = rest.split(BLOCK_END, 1)
        return before.rstrip("\n"), after.lstrip("\n")
    return text.rstrip("\n"), ""


def render_gitignore() -> str:
    text = (
        config.GITIGNORE_FILE.read_text(encoding="utf-8")
        if config.GITIGNORE_FILE.exists()
        else ""
    )
    before, after = split_gitignore(text)
    block = "\n".join([BLOCK_START, *gitignore_lines(), BLOCK_END])
    parts = [p for p in (before, block, after.rstrip("\n")) if p]
    return "\n\n".join(parts) + "\n"


def check_gitignore(fix: bool) -> list:
    wanted = render_gitignore()
    current = (
        config.GITIGNORE_FILE.read_text(encoding="utf-8")
        if config.GITIGNORE_FILE.exists()
        else ""
    )
    if current == wanted:
        return []
    if fix:
        config.GITIGNORE_FILE.write_text(wanted, encoding="utf-8")
        print("  fixed: rewrote the managed block in .gitignore")
        return []
    return ["`.gitignore` managed block is out of date (run with --fix)"]


# ---------------------------------------------------------------------------
# 2-5. Repository state
# ---------------------------------------------------------------------------


def check_private_tracked(files: list, fix: bool) -> list:
    offenders = [f for f in files if config.is_private(f)]
    if not offenders:
        return []
    if fix:
        git("rm", "--cached", "--quiet", "--", *offenders, check=True)
        print(f"  fixed: untracked {len(offenders)} private file(s), local copies kept")
        return []
    return [f"private but still tracked by git: {f}" for f in offenders]


def check_stale_index(files: list, fix: bool) -> list:
    missing = [f for f in files if not (config.ROOT / f).exists()]
    if not missing:
        return []
    if fix:
        git("rm", "--cached", "--quiet", "--", *missing, check=True)
        print(f"  fixed: dropped {len(missing)} stale index entry/entries")
        return []
    return [f"tracked but missing from disk: {f}" for f in missing]


def check_oversized(files: list) -> list:
    large = lfs_files()
    issues = []
    for rel in files:
        path = config.ROOT / rel
        if not path.exists() or rel in large:
            continue
        size_mb = path.stat().st_size / (1024 * 1024)
        if size_mb > config.GITHUB_LIMIT_MB:
            issues.append(
                f"{size_mb:.0f} MB exceeds GitHub's {config.GITHUB_LIMIT_MB} MB limit "
                f"and is not in LFS: {rel}"
            )
    return issues


def check_index() -> list:
    """The built index must cover the corpus and contain nothing guarded.

    A stale index serves results for files that have moved or gone; a leaky one
    publishes the full text of private material in a greppable JSON file that
    stays in git history forever. Both are worse than the equivalent mistake in
    the browse tree, so they are checked separately here.
    """
    import json

    search_dir = config.ROOT / "search"
    manifest_file = search_dir / "manifest.json"
    if not manifest_file.exists():
        return []  # no index built yet; not an error

    try:
        records = json.loads(manifest_file.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"search/manifest.json is unreadable: {exc}"]

    issues = []

    # Nothing guarded may appear, under its own path or as a duplicate alias.
    for record in records:
        for path in [record["path"]] + record.get("also_at", []):
            if config.is_private(path) or config.is_unlisted(path):
                issues.append(f"guarded path present in the search index: {path}")
    if issues:
        return issues  # a leak outranks staleness; fix it first

    from ingest import corpus

    indexed = set()
    for record in records:
        indexed.add(record["path"])
        indexed.update(record.get("also_at", []))
    current = {rel for rel, _ in corpus.publishable_files()}

    missing = sorted(current - indexed)
    extra = sorted(indexed - current)
    if missing:
        issues.append(
            f"{len(missing)} file(s) not in the search index "
            f"(e.g. {missing[0]}) - run scripts/build_index.py"
        )
    if extra:
        issues.append(
            f"{len(extra)} indexed file(s) no longer publishable "
            f"(e.g. {extra[0]}) - run scripts/build_index.py"
        )
    return issues


def check_empty_dirs() -> list:
    issues = []
    for path in sorted(config.ROOT.rglob("*")):
        if not path.is_dir():
            continue
        rel = config.rel_posix(path)
        if any(config.is_infrastructure(part) for part in Path(rel).parts):
            continue
        if not any(path.iterdir()):
            issues.append(f"empty directory: {rel}")
    return issues


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fix", action="store_true", help="apply the fixes that can be applied safely"
    )
    args = parser.parse_args()

    print(f"Guarding {config.ROOT}")
    files = tracked_files()

    issues = []
    issues += check_gitignore(args.fix)
    issues += check_private_tracked(files, args.fix)
    issues += check_stale_index(tracked_files() if args.fix else files, args.fix)
    issues += check_oversized(files)
    issues += check_index()
    issues += check_empty_dirs()

    print()
    if issues:
        print(f"{len(issues)} issue(s) found:")
        for issue in issues:
            print(f"  - {issue}")
        print("\nEmpty directories and oversized files need a human decision.")
        return 1

    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
