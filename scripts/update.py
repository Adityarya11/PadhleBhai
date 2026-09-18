"""
Run the whole pipeline after adding or removing material.

    python scripts/update.py

Does, in order:

    1. normalize_filenames.py   spaces -> underscores (URLs need it)
    2. build_index.py           extract text, rebuild search/
    3. generate_site.py         rebuild the index.html browse tree
    4. guard.py                 check nothing private leaks and nothing is stale

The order matters. Normalising after indexing would leave the index pointing at
the old names, and the guard has to run last because it checks the output of the
two steps before it.

Stops at the first failure rather than pressing on with a half-built index.
"""

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

STEPS = [
    ("Normalising filenames", ["normalize_filenames.py"]),
    ("Building search index", ["build_index.py"]),
    ("Generating index.html", ["generate_site.py"]),
    ("Checking the repo", ["guard.py"]),
]


def main() -> int:
    for number, (label, args) in enumerate(STEPS, 1):
        print(f"\n[{number}/{len(STEPS)}] {label}")
        print("-" * 60)
        result = subprocess.run(
            [sys.executable, str(HERE / args[0])] + args[1:], cwd=HERE.parent
        )
        if result.returncode != 0:
            print(
                f"\n{label} failed (exit {result.returncode}). Nothing further was run."
            )
            if args[0] == "guard.py":
                print(
                    "Fix the issues above, or run `python scripts/guard.py --fix`\n"
                    "for the ones it can handle itself, then re-run this script."
                )
            return result.returncode

    print("\n" + "=" * 60)
    print("Everything is in sync. To publish:")
    print("    git add -A")
    print('    git commit -m "add <course> material"')
    print("    git push")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
