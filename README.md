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
python scripts/build_index.py            # extract text, rebuild search/
python scripts/generate_site.py          # rebuild index.html
python scripts/guard.py                  # verify nothing private leaks
git add -A && git commit -m "add <course> material" && git push
```

`build_index.py` caches extraction in `.index-cache/`, so a rebuild after adding
a few files takes seconds rather than the ~3 minutes of a cold run.

GitHub Actions publishes `main` to GitHub Pages on every push.

## Scripts

| Script                           | What it does                                                                                                                |
| -------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| `scripts/config.py`              | Single source of truth: repo paths, GitHub target, and the guard lists. Everything else imports it.                         |
| `scripts/normalize_filenames.py` | Renames files and folders, spaces to underscores. Uses `git mv` for tracked paths so history follows. `--dry-run` previews. |
| `scripts/generate_site.py`       | Rebuilds `index.html` from the folder tree, applying the guards.                                                            |
| `scripts/build_index.py`         | Extracts text from every publishable file and builds the search index into `search/`.                                       |
| `scripts/search_cli.py`          | Queries the built index from the terminal. The reference implementation of retrieval.                                       |
| `scripts/guard.py`               | Checks the repo is in a publishable state. `--fix` applies what can be fixed safely.                                        |

Run them from the repo root; they locate the root themselves, so the working
directory does not matter.

## Guards — what stays out

Two lists in `scripts/config.py` control visibility:

- **`PRIVATE`** — kept off the site _and_ out of GitHub. Mirrored into the
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

## Search

`search/` holds a static full-text index, built locally and committed. There is
no server: the browser fetches only the shards a query touches.

```
search/meta.json          corpus stats and the shard directory
search/manifest.json      one record per document (436 of them)
search/terms/<xx>.json    postings, sharded by term prefix
search/docs/<id>-<n>.json document text, for snippets and page numbers
```

Try it from the terminal:

```bash
python scripts/search_cli.py matrix chain
python scripts/search_cli.py --explain lecture 5
python scripts/search_cli.py --deep 30 dijkstra   # scan deep into big books
```

**How it is put together.** Retrieval is BM25F over document-level postings.
Unit-level postings were measured at 36.7 MB against 3.9 MB for document-level,
so page numbers and snippets are instead found by scanning the text of the few
documents actually on screen - the same fetch that produces their snippets.

The path and filename are scored as a separate field with their own IDF. That is
what makes `4thSem/DAA/Material/DP/` answer a query for "DAA DP", and what keeps
a well-named 3-page note ahead of a textbook that mentions the topic 5,000 times.

Roughly 96 KB is fetched for a typical query, after a one-time 177 KB for the
manifest.

**Known gaps.** 94 documents are photographed or scanned and carry no text
layer, so they are findable by name and folder only - concentrated in 4th and
5th semester (7th semester and BOOKS are 97% and 93% covered). OCR is backlogged.
One legacy binary `.ppt` cannot be parsed; converting it to `.pptx` would fix it.

## Roadmap

Semantic search once real queries show where the lexical index falls short, and
AI document cards after that.

---

Made with the exhaustion of my B.Tech course.
