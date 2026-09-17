"""
Generate index.html: a static, browsable index of the archive.

The tree is built from the working directory and filtered through the guards in
config.py, so nothing marked PRIVATE or UNLISTED can reach the published page.

Usage:
    python scripts/generate_site.py
"""

import html
import json
import os
import subprocess
import sys
import urllib.parse
from pathlib import Path

import config

# ---------------------------------------------------------------------------
# Type badges shown next to each file
# ---------------------------------------------------------------------------

FILE_TYPE_LABELS = {
    ".pdf": "PDF", ".pptx": "PPT", ".ppt": "PPT",
    ".docx": "DOC", ".doc": "DOC", ".xlsx": "XLS", ".xls": "XLS",
    ".jpg": "IMG", ".jpeg": "IMG", ".png": "IMG", ".gif": "IMG",
    ".zip": "ZIP", ".rar": "ZIP",
    ".py": "PY", ".ipynb": "NB", ".cpp": "C++", ".c": "C", ".h": "H",
    ".txt": "TXT", ".json": "JSON", ".md": "MD",
}

# Rendered by the browser itself.
INLINE_EXTS = {
    ".pdf", ".jpg", ".jpeg", ".png", ".gif",
    ".txt", ".py", ".cpp", ".c", ".h", ".json", ".md",
}

# Rendered by Microsoft's free Office viewer.
OFFICE_EXTS = {".pptx", ".ppt", ".docx", ".doc", ".xlsx", ".xls"}

# Served as raw JSON by Pages, so link to GitHub's notebook renderer instead.
NOTEBOOK_EXTS = {".ipynb"}


# ---------------------------------------------------------------------------
# Page template
# ---------------------------------------------------------------------------

PLACEHOLDER_TOKEN = "__SEARCH_PLACEHOLDER__"


def search_placeholder() -> str:
    """Placeholder text for the search box, sized from the built index."""
    manifest = config.ROOT / "search" / "manifest.json"
    examples = "  (try: matrix chain, lecture 5, deadlock)"
    try:
        records = json.loads(manifest.read_text(encoding="utf-8"))
        pages = sum(record.get("units", 0) for record in records)
        if pages:
            return f"Search {pages:,} pages of material…{examples}"
    except Exception:
        pass
    return f"Search the archive…{examples}"


def _head() -> str:
    """The page header, with the search placeholder filled in.

    A plain replace, not .format(): the template is an f-string, so its escaped
    CSS braces have already collapsed to single braces by this point and any
    further formatting pass would fail on them.
    """
    return HTML_HEAD_TEMPLATE.replace(PLACEHOLDER_TOKEN, search_placeholder())


HTML_HEAD_TEMPLATE = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{config.SITE_TITLE}</title>
    <link rel="stylesheet" href="assets/search.css">
    <style>
        *, *::before, *::after {{ box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', system-ui, sans-serif;
            background-color: #1e1e1e;
            color: #d4d4d4;
            padding: 24px 20px;
            max-width: 960px;
            margin: 0 auto;
        }}
        header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid #3c3c3c;
            padding-bottom: 12px;
            margin-bottom: 16px;
        }}
        header h1 {{
            margin: 0;
            font-size: 1.4rem;
            color: #4ec9b0;
            letter-spacing: 0.02em;
        }}
        .gh-link {{
            display: inline-flex;
            align-items: center;
            gap: 7px;
            text-decoration: none;
            color: #cccccc;
            font-size: 0.85rem;
            padding: 5px 12px;
            border: 1px solid #444;
            border-radius: 6px;
            transition: border-color 0.15s, color 0.15s;
        }}
        .gh-link:hover {{ border-color: #4ec9b0; color: #4ec9b0; }}
        .gh-link svg {{ fill: currentColor; flex-shrink: 0; }}
        ul {{
            list-style-type: none;
            padding-left: 20px;
            margin: 0;
            border-left: 1px solid #2e2e2e;
        }}
        li {{ margin: 3px 0; }}
        details > summary {{
            cursor: pointer;
            padding: 5px 6px;
            border-radius: 4px;
            color: #cccccc;
            font-weight: 500;
            user-select: none;
        }}
        details > summary:hover {{ background-color: #37373d; color: #ffffff; }}
        .file-row {{
            display: flex;
            align-items: center;
            padding: 4px 8px;
            border-radius: 4px;
        }}
        .file-row:hover {{ background-color: #2a2d2e; }}
        .file-icon {{
            font-size: 0.7em;
            font-weight: 600;
            letter-spacing: 0.04em;
            min-width: 34px;
            margin-right: 8px;
            color: #808080;
            flex-shrink: 0;
        }}
        .file-name {{
            flex-grow: 1;
            margin-right: 12px;
            color: #ce9178;
            word-break: break-all;
            font-size: 0.92rem;
        }}
        .btn {{
            text-decoration: none;
            color: #ffffff;
            padding: 2px 9px;
            border-radius: 3px;
            font-size: 0.78em;
            margin-left: 4px;
            white-space: nowrap;
        }}
        .btn-view {{ background-color: #0e639c; }}
        .btn-view:hover {{ background-color: #1177bb; }}
        .btn-dl {{ background-color: #3a3a3a; }}
        .btn-dl:hover {{ background-color: #555; }}
        .lfs-badge {{ background-color: #4a7c2f; cursor: default; }}
        .toolbar {{
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 12px;
        }}
        .btn-collapse {{
            background: none;
            border: 1px solid #444;
            color: #cccccc;
            font-size: 0.82rem;
            padding: 4px 12px;
            border-radius: 5px;
            cursor: pointer;
            transition: border-color 0.15s, color 0.15s;
        }}
        .btn-collapse:hover {{ border-color: #4ec9b0; color: #4ec9b0; }}
        footer {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 28px;
            padding-top: 12px;
            border-top: 1px solid #2e2e2e;
            font-size: 0.78rem;
            color: #6a6a6a;
        }}
        .trex-link {{
            display: inline-flex;
            align-items: center;
            gap: 7px;
            text-decoration: none;
            color: #cccccc;
            padding: 5px 12px;
            border: 1px solid #444;
            border-radius: 6px;
            transition: border-color 0.15s, color 0.15s;
        }}
        .trex-link:hover {{ border-color: #4ec9b0; color: #4ec9b0; }}
        .trex-best strong {{ color: #4ec9b0; font-variant-numeric: tabular-nums; }}
    </style>
</head>
<body>
    <header>
        <h1>{config.SITE_TITLE}</h1>
        <a class="gh-link" href="{config.GITHUB_REPO_URL}" target="_blank" rel="noopener noreferrer">
            <svg height="18" viewBox="0 0 16 16" width="18" aria-hidden="true">
                <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38
                         0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13
                         -.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66
                         .07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15
                         -.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27
                         .68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12
                         .51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48
                         0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8z"/>
            </svg>
            View on GitHub
        </a>
    </header>
    <div class="search-box">
        <input id="q" type="search" autocomplete="off" spellcheck="false"
               placeholder="__SEARCH_PLACEHOLDER__">
    </div>
    <p class="search-hint">Press <kbd>/</kbd> to focus · type <kbd>@</kbd> to look up a document by name</p>
    <div id="search-status"></div>
    <div id="search-panel" hidden>
        <div id="search-results"></div>
    </div>
    <div class="toolbar">
        <button class="btn-collapse" id="toggleAll" onclick="toggleAll()">Expand All</button>
    </div>
    <div id="file-tree">
"""

HTML_FOOT = """    </div>
    <footer>
        <a class="trex-link" href="trex.html">&#129429; Take a study break</a>
        <span class="trex-best">Your best run: <strong id="trex-best">&mdash;</strong></span>
    </footer>
    <script>
        // The game page writes the high score to localStorage under this key;
        // both pages read it, so the footer reflects whatever you last scored.
        (function () {
            try {
                var best = parseInt(localStorage.getItem('padhlebhai.trex.best'), 10);
                if (best > 0) document.getElementById('trex-best').textContent = best;
            } catch (e) {
                // Private browsing or blocked storage - leave the dash in place.
            }
        }());

        // Collapses or expands every <details> element in the file tree.
        // The button label always names the action the next click will take.
        function toggleAll() {
            const btn = document.getElementById('toggleAll');
            const isCollapsing = btn.textContent.trim() === 'Collapse All';
            document.querySelectorAll('#file-tree details').forEach(el => {
                el.open = !isCollapsing;
            });
            btn.textContent = isCollapsing ? 'Expand All' : 'Collapse All';
        }

        // Opens Office documents through Microsoft's free online viewer, which
        // needs a publicly reachable absolute URL as its 'src' parameter.
        function viewOnline(relativePath) {
            const dir = window.location.href.split('?')[0].split('#')[0]
                .replace(/index\\.html$/, '').replace(/\\/?$/, '/');
            const fullUrl = new URL(relativePath, dir).href;
            window.open(
                'https://view.officeapps.live.com/op/view.aspx?src=' + encodeURIComponent(fullUrl),
                '_blank'
            );
        }
    </script>
    <script src="assets/search.js"></script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_lfs_files() -> set:
    """POSIX relative paths of every file stored in Git LFS (empty set if none)."""
    try:
        result = subprocess.run(
            ["git", "-c", "core.quotepath=off", "lfs", "ls-files", "--name-only"],
            capture_output=True, text=True, encoding="utf-8",
            errors="surrogateescape", cwd=config.ROOT,
        )
        return {line.strip() for line in result.stdout.splitlines() if line.strip()}
    except Exception:
        return set()


def lfs_download_url(web_path: str) -> str:
    """Resolve an LFS pointer to its real content through GitHub's media host."""
    return (
        f"https://media.githubusercontent.com/media/"
        f"{config.GITHUB_OWNER}/{config.GITHUB_REPO}/{config.GITHUB_BRANCH}/{web_path}"
    )


def blob_url(web_path: str) -> str:
    """GitHub blob view, which renders notebooks properly."""
    return (
        f"https://github.com/{config.GITHUB_OWNER}/{config.GITHUB_REPO}/"
        f"blob/{config.GITHUB_BRANCH}/{web_path}"
    )


def badge(ext: str) -> str:
    return f'<span class="file-icon">{FILE_TYPE_LABELS.get(ext, "FILE")}</span>'


def view_button(ext: str, web_path: str, is_lfs: bool) -> str:
    """The preview control for a file, or an empty string when none applies."""
    if is_lfs:
        return ('<span class="btn lfs-badge" '
                'title="Large file - download only">LFS</span>')
    if ext in config.NO_PREVIEW_EXTS:
        return ""
    if ext in NOTEBOOK_EXTS:
        return (f'<a href="{blob_url(web_path)}" target="_blank" rel="noopener" '
                f'class="btn btn-view">View</a>')
    if ext in OFFICE_EXTS:
        return (f'<a href="#" onclick="viewOnline(\'{web_path}\'); return false;" '
                f'class="btn btn-view">View Online</a>')
    if ext in INLINE_EXTS:
        return f'<a href="{web_path}" target="_blank" class="btn btn-view">View</a>'
    return ""


# ---------------------------------------------------------------------------
# Tree building
# ---------------------------------------------------------------------------

def build_tree(current: Path, lfs: set, counts: dict) -> str:
    """Render the directory at `current` as a nested <ul>, guards applied.

    Directories with no publishable content are dropped entirely, so a folder
    holding only private material never appears on the page at all.
    """
    items = []
    try:
        entries = sorted(os.scandir(current), key=lambda e: (not e.is_dir(), e.name.lower()))
    except PermissionError:
        return ""

    for entry in entries:
        if config.is_infrastructure(entry.name):
            continue

        path = Path(entry.path)
        rel = config.rel_posix(path)

        if config.is_private(rel):
            counts["private"] += 1
            continue

        if entry.is_dir():
            inner = build_tree(path, lfs, counts)
            if not inner:
                continue
            items.append(
                f'<li><details><summary>{html.escape(entry.name)}</summary>'
                f'{inner}</details></li>'
            )
            continue

        if config.is_unlisted(rel):
            counts["unlisted"] += 1
            continue

        ext = path.suffix.lower()
        web_path = urllib.parse.quote(rel)
        try:
            size_mb = path.stat().st_size / (1024 * 1024)
        except OSError:
            size_mb = 0

        # Anything in the LFS manifest, or simply too large for a normal blob,
        # has to be fetched through the media host rather than from Pages.
        is_lfs = rel in lfs or size_mb > config.GITHUB_LIMIT_MB
        dl_url = lfs_download_url(web_path) if is_lfs else web_path

        counts["listed"] += 1
        items.append(
            f'<li><div class="file-row">{badge(ext)}'
            f'<span class="file-name">{html.escape(entry.name)}</span>'
            f'{view_button(ext, web_path, is_lfs)}'
            f'<a href="{dl_url}" download class="btn btn-dl">Download</a>'
            f'</div></li>'
        )

    if not items:
        return ""
    return "<ul>\n" + "\n".join(items) + "\n</ul>\n"


def main() -> int:
    counts = {"listed": 0, "private": 0, "unlisted": 0}
    lfs = get_lfs_files()

    print(f"Indexing {config.ROOT}")
    tree = build_tree(config.ROOT, lfs, counts)
    config.INDEX_FILE.write_text(_head() + tree + HTML_FOOT, encoding="utf-8")

    # Tells GitHub Pages to serve the files as-is instead of running Jekyll,
    # which would otherwise hide any directory whose name starts with '_'.
    (config.ROOT / ".nojekyll").touch()

    print(f"  listed:   {counts['listed']} file(s)")
    print(f"  private:  {counts['private']} entry/entries held back")
    print(f"  unlisted: {counts['unlisted']} file(s) kept in git but off the page")
    print(f"Written: {config.INDEX_FILE.name}")
    print("\nRun `python scripts/guard.py` before pushing.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
