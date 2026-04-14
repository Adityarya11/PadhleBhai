import os
import shutil
import subprocess
import sys

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ROOT_DIR = "."

# Directories and files excluded from normalization.
# Add entries here to prevent them from being renamed.
IGNORE_DIRS = {
    '.git', '.github', '.vscode',
    '__pycache__', 'node_modules', 'venv', 'bin', 'obj',
}
IGNORE_FILES = {
    'generate_site.py', 'index.html', '.gitignore',
    'README.md', '.nojekyll', 'LICENSE',
    'normalize_filenames.py',  # Don't rename this script itself
}

# Track changes for reporting
RENAMED_FILES = []
RENAMED_DIRS = []
ERRORS = []


def is_in_git_index(filepath: str) -> bool:
    """Check if a file is tracked by git."""
    try:
        result = subprocess.run(
            ['git', 'ls-files', '--error-unmatch', filepath],
            capture_output=True,
            cwd=ROOT_DIR
        )
        return result.returncode == 0
    except Exception:
        return False


def rename_in_git(old_path: str, new_path: str) -> bool:
    """Rename a file in git index to preserve history."""
    try:
        subprocess.run(
            ['git', 'mv', old_path, new_path],
            capture_output=True,
            check=True,
            cwd=ROOT_DIR
        )
        return True
    except Exception as e:
        ERRORS.append(f"Git rename failed for {old_path}: {e}")
        return False


def normalize_name(name: str) -> str:
    """Replace spaces with underscores in a filename."""
    return name.replace(' ', '_')


def normalize_directory(current_path: str, parent_git_tracked: bool = False) -> None:
    """
    Recursively normalize file and directory names.
    
    current_path: the directory to process
    parent_git_tracked: whether the parent directory is git-tracked
    """
    try:
        entries = sorted(os.scandir(current_path), key=lambda e: e.name)
    except PermissionError:
        ERRORS.append(f"Permission denied: {current_path}")
        return

    # Process directories first, then files
    # This ensures we rename parents before children
    for entry in entries:
        if entry.name in IGNORE_FILES or entry.name in IGNORE_DIRS or entry.name.startswith('.'):
            continue

        old_path = os.path.join(current_path, entry.name)
        normalized_name = normalize_name(entry.name)

        # Skip if no change needed
        if normalized_name == entry.name:
            if entry.is_dir():
                # Recurse into unchanged directories
                normalize_directory(old_path, parent_git_tracked)
            continue

        new_path = os.path.join(current_path, normalized_name)
        is_git_tracked = parent_git_tracked and is_in_git_index(
            os.path.relpath(old_path, ROOT_DIR).replace(os.sep, '/')
        )

        try:
            if entry.is_dir():
                # Rename directory
                if is_git_tracked:
                    rename_in_git(
                        os.path.relpath(old_path, ROOT_DIR).replace(os.sep, '/'),
                        os.path.relpath(new_path, ROOT_DIR).replace(os.sep, '/')
                    )
                else:
                    os.rename(old_path, new_path)

                RENAMED_DIRS.append((entry.name, normalized_name, os.path.relpath(new_path, ROOT_DIR)))

                # Recurse into renamed directory
                normalize_directory(new_path, is_git_tracked)

            elif entry.is_file():
                # Rename file
                if is_git_tracked:
                    rename_in_git(
                        os.path.relpath(old_path, ROOT_DIR).replace(os.sep, '/'),
                        os.path.relpath(new_path, ROOT_DIR).replace(os.sep, '/')
                    )
                else:
                    os.rename(old_path, new_path)

                RENAMED_FILES.append((entry.name, normalized_name, os.path.relpath(new_path, ROOT_DIR)))

        except Exception as e:
            ERRORS.append(f"Failed to rename {old_path}: {e}")


def print_summary() -> None:
    """Print a summary of all changes made."""
    print("\n" + "=" * 70)
    print("FILE NAME NORMALIZATION SUMMARY")
    print("=" * 70)

    if RENAMED_FILES:
        print(f"\nFiles Renamed ({len(RENAMED_FILES)}):")
        print("-" * 70)
        for old_name, new_name, path in RENAMED_FILES:
            print(f"  {old_name:40} → {new_name}")
            print(f"    Location: {path}")
    else:
        print("\nNo files to rename.")

    if RENAMED_DIRS:
        print(f"\nDirectories Renamed ({len(RENAMED_DIRS)}):")
        print("-" * 70)
        for old_name, new_name, path in RENAMED_DIRS:
            print(f"  {old_name:40} → {new_name}")
            print(f"    Location: {path}")
    else:
        print("\nNo directories to rename.")

    if ERRORS:
        print(f"\nErrors Encountered ({len(ERRORS)}):")
        print("-" * 70)
        for error in ERRORS:
            print(f"  ⚠ {error}")

    total_changed = len(RENAMED_FILES) + len(RENAMED_DIRS)
    print(f"\nTotal items renamed: {total_changed}")
    print("=" * 70 + "\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("🔄 Starting file name normalization...")
    print(f"   Root directory: {os.path.abspath(ROOT_DIR)}")
    print(f"   Replacing spaces with underscores (_)\n")

    # Check if we're in a git repository
    try:
        subprocess.run(
            ['git', 'rev-parse', '--git-dir'],
            capture_output=True,
            check=True,
            cwd=ROOT_DIR
        )
        is_git_repo = True
        print("   ✓ Git repository detected\n")
    except Exception:
        is_git_repo = False
        print("   ⚠ Not a git repository (files will be renamed without git history)\n")

    # Perform normalization
    normalize_directory(ROOT_DIR, is_git_repo)

    # Print summary
    print_summary()

    if ERRORS:
        print("⚠️  Some errors occurred during normalization. Please review above.")
        sys.exit(1)
    else:
        print("✅ Normalization completed successfully!")
        if is_git_repo and (RENAMED_FILES or RENAMED_DIRS):
            print("\n📝 Remember to commit your changes:")
            print("   git commit -m 'Normalize file names: replace spaces with underscores'")
        sys.exit(0)
