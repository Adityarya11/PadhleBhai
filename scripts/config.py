"""
Shared configuration for the repository maintenance scripts.

Everything the scripts need to agree on lives here: where the repo root is,
which paths are infrastructure, and — most importantly — which material is
*guarded* (kept out of the published site, out of GitHub, or both).

Path patterns
-------------
Every pattern is matched against a POSIX-style path relative to the repo root
(e.g. '7thSem/DIP/Image_Processing_Lab/bottle.jpg').  A pattern matches when it

  * equals the path,
  * is a parent directory of the path ('7thSem/DIP' covers everything inside), or
  * matches it as an fnmatch glob ('*.exe', '*/Lab/*').

Note that '*' crosses '/' here, so '*.exe' matches at any depth.
"""

from fnmatch import fnmatch
from pathlib import Path

# ---------------------------------------------------------------------------
# Locations
# ---------------------------------------------------------------------------

# scripts/config.py -> scripts/ -> repo root
ROOT = Path(__file__).resolve().parents[1]

INDEX_FILE = ROOT / "index.html"
GITIGNORE_FILE = ROOT / ".gitignore"

# ---------------------------------------------------------------------------
# Publishing target
# ---------------------------------------------------------------------------

GITHUB_OWNER = "Adityarya11"
GITHUB_REPO = "PadhleBhai"
GITHUB_BRANCH = "main"
GITHUB_REPO_URL = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}"

# GitHub rejects any single file above this size outside Git LFS.
GITHUB_LIMIT_MB = 100

SITE_TITLE = "College Archives"

# ---------------------------------------------------------------------------
# Infrastructure — repo plumbing, never treated as study material
# ---------------------------------------------------------------------------

INFRA_DIRS = {
    ".git", ".github", ".vscode", ".idea",
    "__pycache__", "node_modules", "venv", ".venv", "bin", "obj",
    "scripts",
}

INFRA_FILES = {
    "index.html", "README.md", "LICENSE",
    ".gitignore", ".gitattributes", ".nojekyll", ".DS_Store",
}

# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------

# PRIVATE: not published *and* not pushed to GitHub.
# guard.py mirrors these into the managed block of .gitignore and reports any
# matching file that is still tracked by git.
PRIVATE = [
    # Coursework that should not be public yet.
    "7thSem/DIP",
    "7thSem/GenAI/Lab",

    # Build output and editor scratch files.
    "*.exe",
    "*.obj",
    "*tempCodeRunnerFile*",
    "*/__pycache__/*",
    "*.pyc",
    ".DS_Store",
]

# UNLISTED: fine to keep in git, but hidden from the generated site because a
# browser cannot do anything useful with them.
UNLISTED = [
    "*.zip",
    "*.rar",
    "*.mp4",
]

# Extensions the site will not render inline even when listed (download only).
NO_PREVIEW_EXTS = {".zip", ".rar", ".mp4", ".exe"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def rel_posix(path) -> str:
    """Return `path` as a POSIX-style path relative to the repo root."""
    return Path(path).resolve().relative_to(ROOT).as_posix()


def matches(rel: str, patterns) -> bool:
    """True if `rel` (a POSIX relative path) matches any of `patterns`."""
    for pattern in patterns:
        pattern = pattern.rstrip("/")
        if rel == pattern or rel.startswith(pattern + "/"):
            return True
        if fnmatch(rel, pattern):
            return True
    return False


def is_infrastructure(name: str) -> bool:
    """True for repo plumbing: dotfiles, script folder, generated output."""
    return name in INFRA_DIRS or name in INFRA_FILES or name.startswith(".")


def is_private(rel: str) -> bool:
    """True if the path must stay off both the site and GitHub."""
    return matches(rel, PRIVATE)


def is_unlisted(rel: str) -> bool:
    """True if the path may live in git but must not appear on the site."""
    return matches(rel, UNLISTED)


def is_published(rel: str) -> bool:
    """True if the path should appear in the generated index."""
    return not is_private(rel) and not is_unlisted(rel)
