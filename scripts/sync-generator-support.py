#!/usr/bin/env python3
"""Keep the generator support page in step with what conformance proved.

`ComlineProject/generation`'s conformance suite checks every generator's
feature claims against its corpus and writes the result to `FEATURES.md` at
the repository root. This copies that file's matrix into
`docs/docs/reference/generator-support.md`, between its
`<!-- features:start -->` / `<!-- features:end -->` markers, so the page says
exactly what was proven. The issue references in it (`core#96`) become links.

    python3 scripts/sync-generator-support.py            # rewrite the page
    python3 scripts/sync-generator-support.py --check    # exit 1 on drift
    python3 scripts/sync-generator-support.py --file ../generation/FEATURES.md

Stdlib only: no Rust toolchain needed, so CI runs it per pull request.
"""

from __future__ import annotations

import argparse
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "docs/docs/reference/generator-support.md"
RAW = "https://raw.githubusercontent.com/ComlineProject/generation/{rev}/FEATURES.md"
START = "<!-- features:start -->"
END = "<!-- features:end -->"

# Repositories an issue reference may name; anything else is left as text
# (`rust#1.70.0` is a target, not an issue).
REPOS = ("core", "generation", "cli", "comline-rust", "comline-typescript", "language-server", "runtime", "docs")
ISSUE_RE = re.compile(r"\b(" + "|".join(re.escape(r) for r in REPOS) + r")#(\d+)\b(?![\d.])")


def read_features(file: Path | None, rev: str) -> str:
    if file:
        return file.read_text(encoding="utf-8")
    url = RAW.format(rev=rev)
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            return response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        sys.exit(f"error: fetching {url} failed ({error.code} {error.reason})")
    except urllib.error.URLError as error:
        sys.exit(f"error: fetching {url} failed ({error.reason})")


def section(features: str) -> str:
    """The marked section the page should hold: the matrix, issues linked."""
    table = [line for line in features.splitlines() if line.startswith("|")]
    if not table:
        sys.exit("error: FEATURES.md has no table")
    linked = "\n".join(
        ISSUE_RE.sub(lambda m: f"[{m[0]}](https://github.com/ComlineProject/{m[1]}/issues/{m[2]})", line)
        for line in table
    )
    return (
        f"{START}\n"
        "<!-- Copied from ComlineProject/generation's FEATURES.md by "
        "scripts/sync-generator-support.py - don't edit by hand. -->\n\n"
        f"{linked}\n\n{END}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="exit 1 if the page is out of date")
    parser.add_argument("--file", type=Path, help="read FEATURES.md from here instead of fetching it")
    parser.add_argument("--rev", default="master", help="generation revision to fetch (default: master)")
    args = parser.parse_args()

    page = PAGE.read_text(encoding="utf-8")
    start, end = page.find(START), page.find(END)
    if start < 0 or end < 0:
        sys.exit(f"error: {PAGE.relative_to(ROOT)} has no {START} ... {END} section")
    current = page[start : end + len(END)]
    wanted = section(read_features(args.file, args.rev))

    if current == wanted:
        print("generator support page is up to date")
        return 0
    if args.check:
        print(f"{PAGE.relative_to(ROOT)} is out of date with generation's FEATURES.md.")
        print("Run: python3 scripts/sync-generator-support.py")
        return 1
    PAGE.write_text(page[:start] + wanted + page[end + len(END) :], encoding="utf-8")
    print(f"updated {PAGE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
