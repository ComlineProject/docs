#!/usr/bin/env python3
"""Check every IDL keyword in core's grammar is documented in the guide.

The grammar declares each keyword as `#[rust_sitter::leaf(text = "...")]`, so
the language's real token set is machine-readable. The guide pages are written
by hand and say far more than a token list ever could — so, like the CLI
checker, this generates nothing. It catches one failure: a keyword landing in
the language and never reaching the docs.

No Rust build and no local checkout needed — the grammar is a source file, read
from a checkout if one is at hand, otherwise fetched from GitHub.

    python3 scripts/check-idl-drift.py
    python3 scripts/check-idl-drift.py --checkout ../core   # skip the fetch
    python3 scripts/check-idl-drift.py --rev <sha>          # pin the grammar

A keyword counts as documented when it appears as a whole word inside a code
fence or an inline code span. Both halves of that matter: searching prose for
bare words matches English ("the *type* of a field", "a *package* depends on"),
while searching only for `backticked` mentions misses keywords that appear just
in an example — which is where most of them legitimately live.
"""

from __future__ import annotations

import argparse
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = "https://raw.githubusercontent.com/ComlineProject/core"

# Each grammar and the docs that are expected to cover it.
#
# `core/src/package/config/idl/grammar.rs` (the `config.idp` grammar) is not
# listed yet: `reference/congregation/config-id.md` is still an empty stub, so
# checking it would report `false` as undocumented every run for a reason that
# has nothing to do with drift — and a check that is always red gets ignored.
# Add it here once that page is written; it is only three keywords
# (`congregation`, `true`, `false`).
GRAMMARS = [
    (
        "core/src/schema/idl/grammar.rs",
        "the IDL guide",
        ["docs/docs/guide/idl"],
    ),
]

# Keywords the grammar has but the docs deliberately do not teach.
EXCLUDED = {
    "import": "legacy, superseded by `use` — grammar keeps it for "
    "backward compatibility and the guide teaches `use` only",
}

LEAF_RE = re.compile(r'leaf\(text\s*=\s*"([^"]+)"')
KEYWORD_RE = re.compile(r"^[a-z][a-z0-9_]*$")
FENCE_RE = re.compile(r"^(?:[ \t]*)(?:```|~~~)", re.MULTILINE)
INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")


def read_grammar(path: str, checkout: Path | None, rev: str) -> str:
    """Read a grammar file from a local checkout, else fetch it."""
    if checkout:
        local = checkout / path
        if not local.exists():
            sys.exit(f"error: {local} not found — is --checkout a `core` checkout?")
        return local.read_text(encoding="utf-8")

    url = f"{RAW}/{rev}/{path}"
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            return response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        sys.exit(f"error: fetching {url} failed ({error.code} {error.reason})")
    except urllib.error.URLError as error:
        sys.exit(f"error: fetching {url} failed ({error.reason})")


def keywords(grammar: str) -> set[str]:
    """The identifier-like leaf tokens — keywords and primitive type names."""
    return {t for t in LEAF_RE.findall(grammar) if KEYWORD_RE.match(t)}


def code_regions(markdown: str) -> str:
    """Everything inside a code fence or an inline code span, concatenated.

    Prose is deliberately dropped: an English sentence using "type" or
    "package" is not documentation of the keyword.
    """
    regions = []
    # Fenced blocks: split on fence markers and keep the odd-indexed pieces.
    # A page with an unterminated fence would mis-split, so the trailing
    # piece of an odd-length split is ignored rather than guessed at.
    pieces = FENCE_RE.split(markdown)
    for index, piece in enumerate(pieces):
        if index % 2 == 1:
            regions.append(piece)
    regions.extend(INLINE_CODE_RE.findall(markdown))
    return "\n".join(regions)


def documented(dirs: list[str]) -> tuple[str, int]:
    """Concatenated code regions of every Markdown page under `dirs`."""
    regions, pages = [], 0
    for directory in dirs:
        base = ROOT / directory
        if not base.is_dir():
            continue
        for page in sorted(base.rglob("*.md")):
            regions.append(code_regions(page.read_text(encoding="utf-8")))
            pages += 1
    return "\n".join(regions), pages


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--checkout",
        type=Path,
        help="path to a local `core` checkout (skips the network fetch)",
    )
    parser.add_argument(
        # `core`'s default branch is `master` (the CLI's is `main` — they
        # differ, so neither is a safe guess for the other).
        "--rev", default="master", help="core revision to fetch (default: master)"
    )
    args = parser.parse_args()

    drift = False
    for path, label, dirs in GRAMMARS:
        grammar = read_grammar(path, args.checkout, args.rev)
        tokens = keywords(grammar) - set(EXCLUDED)
        if not tokens:
            sys.exit(f"error: no leaf tokens found in {path} — did the grammar change shape?")

        surface, pages = documented(dirs)
        if not pages:
            sys.exit(f"error: no Markdown pages found under {', '.join(dirs)}")

        missing = {
            token
            for token in tokens
            if not re.search(rf"\b{re.escape(token)}\b", surface)
        }
        print(
            f"{path}: {len(tokens)} keywords vs {label} ({pages} pages)"
            f"{f', {len(EXCLUDED)} excluded' if EXCLUDED else ''}"
        )
        if missing:
            drift = True
            for token in sorted(missing):
                print(f"  + {token:<14} in the grammar, not documented")

    if drift:
        print("\nDrift found: document the keywords above, or teach the script why not.")
        return 1
    print("\nNo drift: every grammar keyword is documented.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
