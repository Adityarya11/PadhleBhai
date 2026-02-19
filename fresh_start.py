import os
import urllib.parse
import html

# --- CONFIGURATION ---
ROOT_DIR = "."
OUTPUT_FILE = "index.html"
GITHUB_LIMIT_MB = 100  # Max file size allowed by GitHub (Standard)

# Standard Ignore List
IGNORE_DIRS = {'.git', '.github', '.vscode', '__pycache__', 'node_modules', 'venv', 'bin', 'obj'}
IGNORE_FILES = {'fresh_start.py', 'index.html', '.gitignore', 'README.md', '.nojekyll', 'LICENSE'}

html_head = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>College Archives</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background-color: #1e1e1e; color: #d4d4d4; padding: 20px; max-width: 900px; margin: 0 auto; }
        h1 { border-bottom: 1px solid #3c3c3c; padding-bottom: 10px; color: #4ec9b0; }
        ul { list-style-type: none; padding-left: 20px; margin: 0; border-left: 1px solid #333; }
        li { margin: 4px 0; }
        details > summary { cursor: pointer; padding: 6px; border-radius: 4px; color: #cccccc; font-weight: 500; }
        details > summary:hover { background-color: #37373d; color: #fff; }
        .file-row { display: flex; align-items: center; padding: 4px 8px; border-radius: 4px; }
        .file-row:hover { background-color: #2a2d2e; }
        .file-name { flex-grow: 1; margin-right: 15px; color: #ce9178; word-break: break-all; }
        .btn { text-decoration: none; color: white; padding: 3px 10px; border-radius: 3px; font-size: 0.8em; margin-left: 5px; }
        .btn-view { background-color: #0e639c; } 
        .btn-dl { background-color: #444; }
        .warning { color: #ce9178; font-size: 0.9em; margin-bottom: 10px; }
    </style>
</head>
<body>
    <h1>📂 Repository Browser</h1>
    <div id="file-tree">
"""

html_foot = """
    </div>
    <script>
        function viewOnline(relativePath) {
            const baseUrl = window.location.origin + window.location.pathname.replace('index.html', '').replace(/\/$/, '') + '/';
            const cleanPath = relativePath.replace(/^\\.\\//, '');
            const fullUrl = baseUrl + cleanPath;
            const viewerUrl = 'https://view.officeapps.live.com/op/view.aspx?src=' + encodeURIComponent(fullUrl);
            window.open(viewerUrl, '_blank');
        }
    </script>
</body>
</html>
"""

def get_file_icon(ext):
    icons = {'.pdf':'📕', '.pptx':'📊', '.docx':'📝', '.jpg':'🖼️', '.png':'🖼️', '.zip':'📦', '.py':'💻'}
    return icons.get(ext, '📄')

def check_large_files():
    """Finds files > 100MB and adds them to .gitignore"""
    large_files = []
    print("🔍 Scanning for large files (>100MB)...")
    
    for root, dirs, files in os.walk(ROOT_DIR):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for name in files:
            filepath = os.path.join(root, name)
            try:
                size_mb = os.path.getsize(filepath) / (1024 * 1024)
                if size_mb > GITHUB_LIMIT_MB:
                    rel_path = os.path.relpath(filepath, ROOT_DIR)
                    large_files.append(rel_path)
                    print(f"   ❌ Too big ({size_mb:.1f}MB): {rel_path}")
            except OSError:
                pass
                
    if large_files:
        with open(".gitignore", "a") as f:
            for lf in large_files:
                f.write(f"\n{lf}")
        print(f"⚠️  Added {len(large_files)} large files to .gitignore (They will NOT be uploaded).")
    else:
        print("✅ No large files found.")

def build_tree_html(current_path):
    html_output = "<ul>"
    
    try:
        with os.scandir(current_path) as entries:
            entry_list = sorted(list(entries), key=lambda e: (not e.is_dir(), e.name.lower()))

            for entry in entry_list:
                if entry.name in IGNORE_FILES or entry.name in IGNORE_DIRS or entry.name.startswith('.'): continue
                
                if entry.is_dir():
                    html_output += f"""<li><details><summary>📁 {html.escape(entry.name)}</summary>{build_tree_html(entry.path)}</details></li>"""
                
                elif entry.is_file():
                    ext = os.path.splitext(entry.name)[1].lower()
                    
                    # 1. Path Calculation
                    rel_path = os.path.relpath(entry.path, ROOT_DIR)
                    clean_path = rel_path.replace(os.sep, '/') # Web uses forward slash
                    web_path = urllib.parse.quote(clean_path)   # Encodes spaces/symbols
                    
                    icon = get_file_icon(ext)
                    
                    # 2. Check if file exceeds GitHub's size limit (kept in LFS, not viewable on Pages)
                    try:
                        size_mb = os.path.getsize(entry.path) / (1024 * 1024)
                    except OSError:
                        size_mb = 0
                    is_lfs = size_mb > GITHUB_LIMIT_MB
                    
                    # 3. Buttons
                    view_btn = ""
                    if is_lfs:
                        view_btn = '<span class="btn" style="background-color:#6c3; cursor:default;" title="File too large for online preview">⚠ LFS</span>'
                    elif ext in ['.pdf', '.jpg', '.png', '.txt', '.py', '.cpp', '.c']:
                        view_btn = f'<a href="{web_path}" target="_blank" class="btn btn-view">View</a>'
                    elif ext in ['.pptx', '.docx', '.xlsx']:
                        view_btn = f'<a href="#" onclick="viewOnline(\'{web_path}\'); return false;" class="btn btn-view">View Online</a>'
                    
                    html_output += f"""
                    <li><div class="file-row"><span>{icon} </span><span class="file-name">{html.escape(entry.name)}</span>{view_btn}<a href="{web_path}" download class="btn btn-dl">⬇</a></div></li>
                    """

    except PermissionError: pass
    return html_output + "</ul>"

if __name__ == "__main__":
    # Step 1: Handle big files
    if not os.path.exists(".gitignore"):
        with open(".gitignore", "w") as f: f.write(".DS_Store\n__pycache__/\n*.pyc\n")
    check_large_files()

    # Step 2: Generate Site
    print("🚀 Generating index.html...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html_head + build_tree_html(ROOT_DIR) + html_foot)
    
    # Step 3: Create .nojekyll to allow folders starting with underscore
    with open(".nojekyll", "w") as f: pass
    
    print("\n✅ READY! Run these commands now:")
    print("   git init")
    print("   git add .")
    print("   git commit -m 'Fresh start'")
    print("   git branch -M main")
    print("   git remote add origin <YOUR_REPO_URL>")
    print("   git push -u origin main")