# PadhleBhai — College Study Material Archive

Course material from my B.Tech, from 4th semester onward, kept in one place and
published as a static browsable index.

**Live site:** https://adityarya11.github.io/PadhleBhai/

---

## Layout

```
4thSem/ 5thSem/ 6thSem/ 7thSem/   material, one folder per course
BOOKS/                            reference books, not tied to a semester
scripts/                          maintenance tooling (see below)
index.html                        generated - never edit by hand
```

Names use underscores instead of spaces so every path works as a URL without
escaping. `scripts/normalize_filenames.py` enforces that.

## Adding material

```bash
# 1. drop the files into the right semester/course folder, then:
python scripts/normalize_filenames.py    # spaces -> underscores
python scripts/generate_site.py          # rebuild index.html
python scripts/guard.py                  # verify nothing private leaks
git add -A && git commit -m "add <course> material" && git push
```

GitHub Actions publishes `main` to GitHub Pages on every push.

## Scripts

| Script | What it does |
| --- | --- |
| `scripts/config.py` | Single source of truth: repo paths, GitHub target, and the guard lists. Everything else imports it. |
| `scripts/normalize_filenames.py` | Renames files and folders, spaces to underscores. Uses `git mv` for tracked paths so history follows. `--dry-run` previews. |
| `scripts/generate_site.py` | Rebuilds `index.html` from the folder tree, applying the guards. |
| `scripts/guard.py` | Checks the repo is in a publishable state. `--fix` applies what can be fixed safely. |

Run them from the repo root; they locate the root themselves, so the working
directory does not matter.

## Guards — what stays out

Two lists in `scripts/config.py` control visibility:

- **`PRIVATE`** — kept off the site *and* out of GitHub. Mirrored into the
  managed block of `.gitignore` by `guard.py --fix`. Currently covers
  `7thSem/DIP`, `7thSem/GenAI/Lab`, executables, and editor scratch files.
- **`UNLISTED`** — still committed, but hidden from the page because a browser
  cannot do anything useful with them (`.zip`, `.rar`, `.mp4`).

To hide something new, add a pattern to `PRIVATE` and run:

```bash
python scripts/guard.py --fix      # updates .gitignore, untracks the files
python scripts/generate_site.py    # drops them from the page
```

A pattern matches a path if it equals it, is a parent folder of it, or matches
it as a glob (`*` crosses `/`, so `*.exe` matches at any depth).

Note that `.gitignore` alone does **not** remove an already-committed file —
`guard.py` catches exactly that case. Untracking keeps your local copy; it only
stops the file being pushed, and it stays in past commits.

`guard.py` also reports stale index entries, empty folders, and files over
GitHub's 100 MB limit that are not in Git LFS.

## Large files

Anything above 100 MB must go through Git LFS and needs a matching rule in
`.gitattributes`. On the site these show an `LFS` badge and download through
`media.githubusercontent.com`, since Pages serves only the pointer file.

## Viewing

PDFs, images, and source files open inline. Office documents open through
Microsoft's online viewer, notebooks through GitHub's renderer — both need the
file to be publicly reachable, so neither works for private material.

## Roadmap

The cleanup above is groundwork for making this actually searchable: full-text
search over the index, per-course metadata, and a better browsing UI.

---

Made with the exhaustion of my B.Tech course.
