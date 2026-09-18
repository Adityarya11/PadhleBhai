"""
Normalize file and directory names across the archive.

Spaces become underscores, so that every path is safe to use in a URL without
percent-encoding.  Git-tracked entries are moved with `git mv` so history
follows the rename; everything else is renamed on disk.

Usage:
    python scripts/normalize_filenames.py            # apply
    python scripts/normalize_filenames.py --dry-run  # show what would change
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

import config

RENAMED_FILES = []
RENAMED_DIRS = []
ERRORS = []


def git_available() -> bool:
    """True if the repo root is inside a git working tree."""
    try:
        subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True,
            check=True,
            cwd=config.ROOT,
        )
        return True
    except Exception:
        return False


def is_tracked(rel: str) -> bool:
    """True if git already knows about this path (file or directory)."""
    try:
        result = subprocess.run(
            ["git", "ls-files", "--error-unmatch", "--", rel],
            capture_output=True,
            cwd=config.ROOT,
        )
        return result.returncode == 0
    except Exception:
        return False


def normalize_name(name: str) -> str:
    """Spaces to underscores, collapsing any run of them into one."""
    parts = [p for p in name.split(" ") if p]
    return "_".join(parts)


def move(old: Path, new: Path, tracked: bool, dry_run: bool) -> bool:
    """Rename `old` to `new`, via git when the path is tracked."""
    if dry_run:
        return True
    try:
        if tracked:
            subprocess.run(
                [
                    "git",
                    "mv",
                    "--",
                    config.rel_posix(old),
                    new.relative_to(config.ROOT).as_posix(),
                ],
                capture_output=True,
                check=True,
                cwd=config.ROOT,
            )
        else:
            os.rename(old, new)
        return True
    except Exception as exc:
        ERRORS.append(f"Failed to rename {config.rel_posix(old)}: {exc}")
        return False


def normalize_directory(current: Path, use_git: bool, dry_run: bool) -> None:
    """Recursively normalize names under `current`, parents before children."""
    try:
        entries = sorted(os.scandir(current), key=lambda e: e.name)
    except PermissionError:
        ERRORS.append(f"Permission denied: {current}")
        return

    for entry in entries:
        if config.is_infrastructure(entry.name):
            continue

        old_path = Path(entry.path)
        normalized = normalize_name(entry.name)

        if normalized == entry.name:
            if entry.is_dir():
                normalize_directory(old_path, use_git, dry_run)
            continue

        new_path = old_path.with_name(normalized)
        rel_old = config.rel_posix(old_path)

        if new_path.exists():
            ERRORS.append(f"Target already exists, skipped: {rel_old} -> {normalized}")
            if entry.is_dir():
                normalize_directory(old_path, use_git, dry_run)
            continue

        tracked = use_git and is_tracked(rel_old)
        if not move(old_path, new_path, tracked, dry_run):
            continue

        record = (entry.name, normalized, str(new_path.parent.relative_to(config.ROOT)))
        if entry.is_dir():
            RENAMED_DIRS.append(record)
            # On a dry run the directory was not actually moved, so keep walking
            # the original path.
            normalize_directory(old_path if dry_run else new_path, use_git, dry_run)
        else:
            RENAMED_FILES.append(record)


def print_summary(dry_run: bool) -> None:
    heading = "PLANNED RENAMES" if dry_run else "FILE NAME NORMALIZATION SUMMARY"
    print("\n" + "=" * 70)
    print(heading)
    print("=" * 70)

    for label, records in (("Directories", RENAMED_DIRS), ("Files", RENAMED_FILES)):
        if not records:
            print(f"\n{label}: nothing to rename.")
            continue
        print(f"\n{label} ({len(records)}):")
        print("-" * 70)
        for old_name, new_name, location in records:
            print(f"  {old_name}")
            print(f"    -> {new_name}   [{location}]")

    if ERRORS:
        print(f"\nProblems ({len(ERRORS)}):")
        print("-" * 70)
        for error in ERRORS:
            print(f"  ! {error}")

    print(f"\nTotal: {len(RENAMED_FILES) + len(RENAMED_DIRS)} item(s)")
    print("=" * 70 + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="report the renames without touching anything",
    )
    args = parser.parse_args()

    print("Normalizing names (spaces -> underscores)")
    print(f"  Root: {config.ROOT}")

    use_git = git_available()
    print(
        "  Git:  "
        + (
            "tracked files move with `git mv`"
            if use_git
            else "not a git repo, renaming on disk only"
        )
    )
    if args.dry_run:
        print("  Mode: dry run, nothing will be changed")

    normalize_directory(config.ROOT, use_git, args.dry_run)
    print_summary(args.dry_run)

    if ERRORS:
        return 1
    if (RENAMED_FILES or RENAMED_DIRS) and not args.dry_run:
        print("Names changed - regenerate the site:")
        print("  python scripts/generate_site.py\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
