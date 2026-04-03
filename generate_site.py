import os
import subprocess
import urllib.parse
import html

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ROOT_DIR = "."
OUTPUT_FILE = "index.html"

# GitHub free plan enforces a 100 MB hard limit per file outside LFS.
GITHUB_LIMIT_MB = 100

GITHUB_OWNER = "Adityarya11"
GITHUB_REPO = "PadhleBhai"
GITHUB_BRANCH = "main"

# Directories and files excluded from the generated tree.
# Add entries here to suppress them from the public index.
IGNORE_DIRS = {
    '.git', '.github', '.vscode',
    '__pycache__', 'node_modules', 'venv', 'bin', 'obj',
}
IGNORE_FILES = {
    'generate_site.py', 'index.html', '.gitignore',
    'README.md', '.nojekyll', 'LICENSE',
}

# ---------------------------------------------------------------------------
# HTML Template
# ---------------------------------------------------------------------------

# GITHUB_REPO_URL is interpolated into the header link at generation time.
GITHUB_REPO_URL = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}"

html_head = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>College Archives</title>
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
            font-size: 0.85em;
            margin-right: 6px;
            opacity: 0.75;
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
        .lfs-badge {{
            background-color: #4a7c2f;
            cursor: default;
        }}
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
    </style>
</head>
<body>
    <header>
        <h1>College Archives</h1>
        <a class="gh-link" href="{GITHUB_REPO_URL}" target="_blank" rel="noopener noreferrer">
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
    <div class="toolbar">
        <button class="btn-collapse" id="toggleAll" onclick="toggleAll()">Collapse All</button>
    </div>
    <div id="file-tree">
"""

html_foot = """    </div>
    <script>
        // Collapses or expands every <details> element in the file tree.
        // Button label reflects the action that will be taken on next click.
        function toggleAll() {
            const btn = document.getElementById('toggleAll');
            const isCollapsing = btn.textContent.trim() === 'Collapse All';
            document.querySelectorAll('#file-tree details').forEach(el => {
                el.open = !isCollapsing;
            });
            btn.textContent = isCollapsing ? 'Expand All' : 'Collapse All';
        }

        // Opens Office documents via Microsoft's free online viewer.
        // The viewer accepts a publicly accessible URL as the 'src' query parameter.
        function viewOnline(relativePath) {
            const base = window.location.origin
                + window.location.pathname.replace('index.html', '').replace(/\/$/, '') + '/';
            const fullUrl = base + relativePath.replace(/^\.\//, '');
            window.open(
                'https://view.officeapps.live.com/op/view.aspx?src=' + encodeURIComponent(fullUrl),
                '_blank'
            );
        }
    </script>
</body>
</html>
"""

# ---------------------------------------------------------------------------
# File type labels used as visible badges in the tree listing.
# Keys are lowercase extensions; unknown types fall back to 'FILE'.
# ---------------------------------------------------------------------------
FILE_TYPE_LABELS = {
    '.pdf':  '📕',
    '.pptx': 'PPT',
    '.ppt':  'PPT',
    '.docx': 'DOC',
    '.doc':  'DOC',
    '.xlsx': 'XLS',
    '.xls':  'XLS',
    '.jpg':  'IMG',
    '.jpeg': 'IMG',
    '.png':  'IMG',
    '.gif':  'IMG',
    '.zip':  'ZIP',
    '.rar':  'ZIP',
    '.py':   'PY',
    '.cpp':  '📜',
    '.c':    'C',
    '.h':    'H',
    '.txt':  'TXT',
    '.ipynb':'📒',
    '.exe':'📜',
}


def get_file_badge(ext: str) -> str:
    """Return an HTML span acting as a small type badge for the given extension."""
    label = FILE_TYPE_LABELS.get(ext.lower(), 'FILE')
    return f'<span class="file-icon">{label}</span>'


def get_lfs_files() -> set:
    """
    Query Git LFS for every file pointer tracked in the current repo.
    Returns a set of POSIX-style relative paths (e.g. '4thSem/COA/Notes.pdf').
    Returns an empty set if git-lfs is unavailable or the repo has no LFS files.
    """
    try:
        result = subprocess.run(
            ['git', 'lfs', 'ls-files', '--name-only'],
            capture_output=True, text=True, cwd=ROOT_DIR
        )
        return {line.strip() for line in result.stdout.splitlines() if line.strip()}
    except Exception:
        return set()


def get_lfs_download_url(web_path: str) -> str:
    """
    Build a media.githubusercontent.com URL so that LFS pointer files are
    resolved to their actual binary content when downloaded from the page.
    web_path must already be URL-encoded.
    """
    return (
        f"https://media.githubusercontent.com/media/"
        f"{GITHUB_OWNER}/{GITHUB_REPO}/{GITHUB_BRANCH}/{web_path}"
    )


def check_large_files() -> None:
    """
    Walk the repository tree and identify files that exceed GITHUB_LIMIT_MB
    and are not tracked by Git LFS.  Any such files are appended to .gitignore
    so they are not accidentally pushed and rejected by GitHub.
    """
    lfs_files = get_lfs_files()
    oversized = []
    print(f"Scanning for files larger than {GITHUB_LIMIT_MB} MB ...")

    for root, dirs, files in os.walk(ROOT_DIR):
        # Prune ignored directories so os.walk does not descend into them.
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for name in files:
            filepath = os.path.join(root, name)
            try:
                size_mb = os.path.getsize(filepath) / (1024 * 1024)
            except OSError:
                continue

            if size_mb <= GITHUB_LIMIT_MB:
                continue

            rel_path = os.path.relpath(filepath, ROOT_DIR).replace(os.sep, '/')
            if rel_path in lfs_files:
                print(f"  [LFS]  {size_mb:.1f} MB  {rel_path}")
            else:
                oversized.append(rel_path)
                print(f"  [SKIP] {size_mb:.1f} MB  {rel_path}  (will be added to .gitignore)")

    if oversized:
        with open(".gitignore", "a") as fh:
            for path in oversized:
                fh.write(f"\n{path}")
        print(f"Added {len(oversized)} oversized file(s) to .gitignore.")
    else:
        print("No oversized files found outside LFS.")


def build_tree_html(current_path: str, lfs_files: set | None) -> str:
    """
    Recursively build an HTML <ul> tree for the directory at current_path.

    Directories render as collapsible <details> elements.
    Files render with:
      - a type badge (PDF / CPP / etc.)
      - a View button for browser-renderable formats
      - a View Online button for Office documents (via Microsoft viewer)
      - a Download button (redirected through media.githubusercontent.com for LFS files)

    lfs_files: set of POSIX relative paths tracked by Git LFS, used to
               rewrite download URLs so LFS pointer files resolve correctly.
    """
    if lfs_files is None:
        lfs_files = get_lfs_files()

    html_output = "<ul>\n"

    try:
        with os.scandir(current_path) as entries:
            # Directories first, then files; both sorted case-insensitively.
            entry_list = sorted(
                entries,
                key=lambda e: (not e.is_dir(), e.name.lower())
            )

            for entry in entry_list:
                if (
                    entry.name in IGNORE_FILES
                    or entry.name in IGNORE_DIRS
                    or entry.name.startswith('.')
                ):
                    continue

                if entry.is_dir():
                    html_output += (
                        f'<li><details><summary>{html.escape(entry.name)}</summary>'
                        f'{build_tree_html(entry.path, lfs_files)}'
                        f'</details></li>\n'
                    )

                elif entry.is_file():
                    ext = os.path.splitext(entry.name)[1].lower()
                    rel_path = os.path.relpath(entry.path, ROOT_DIR).replace(os.sep, '/')
                    web_path = urllib.parse.quote(rel_path)
                    badge = get_file_badge(ext)

                    try:
                        size_mb = os.path.getsize(entry.path) / (1024 * 1024)
                    except OSError:
                        size_mb = 0

                    # A file qualifies as LFS if it is registered in the LFS
                    # manifest or if it physically exceeds the GitHub file size limit.
                    is_lfs = (rel_path in lfs_files) or (size_mb > GITHUB_LIMIT_MB)

                    if is_lfs:
                        # LFS files cannot be previewed; redirect download through
                        # media.githubusercontent.com to bypass the pointer file.
                        view_btn = (
                            '<span class="btn lfs-badge" '
                            'title="Stored in Git LFS — direct download only">LFS</span>'
                        )
                        dl_url = get_lfs_download_url(web_path)
                    else:
                        dl_url = web_path
                        if ext in {'.pdf', '.jpg', '.jpeg', '.png', '.txt', '.py', '.cpp', '.c', '.h', '.ipynb'}:
                            view_btn = f'<a href="{web_path}" target="_blank" class="btn btn-view">View</a>'
                        elif ext in {'.pptx', '.ppt', '.docx', '.doc', '.xlsx', '.xls'}:
                            view_btn = (
                                f'<a href="#" onclick="viewOnline(\'{web_path}\'); return false;" '
                                f'class="btn btn-view">View Online</a>'
                            )
                        else:
                            view_btn = ''

                    html_output += (
                        f'<li><div class="file-row">'
                        f'{badge}'
                        f'<span class="file-name">{html.escape(entry.name)}</span>'
                        f'{view_btn}'
                        f'<a href="{dl_url}" download class="btn btn-dl">Download</a>'
                        f'</div></li>\n'
                    )

    except PermissionError:
        pass

    return html_output + "</ul>\n"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Ensure .gitignore exists with baseline rules before appending to it.
    if not os.path.exists(".gitignore"):
        with open(".gitignore", "w") as fh:
            fh.write(".DS_Store\n__pycache__/\n*.pyc\n")

    check_large_files()

    print(f"Generating {OUTPUT_FILE} ...")
    lfs_files = get_lfs_files()
    with open(OUTPUT_FILE, "w", encoding="utf-8") as fh:
        fh.write(html_head + build_tree_html(ROOT_DIR, lfs_files) + html_foot)
    print(f"Written: {OUTPUT_FILE}")

    # .nojekyll tells GitHub Pages to skip Jekyll processing.
    # Required so that directories starting with '_' are served correctly.
    with open(".nojekyll", "w") as fh:
        pass
    print("Done.")
    
    