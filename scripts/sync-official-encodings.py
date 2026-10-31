#!/usr/bin/env python3
"""Render the official encodings' profile tables into the reference page.

The official encodings package (`packed@1`, `datagram@2`, `comline@1`, ...)
is embedded in core, at `core_stdlib/packages/comline/`: a `config.idp`
declaring each encoding with its kind and profile, and the profiles
themselves (`profiles/<name>.json`), copied from the runtime's conformance
corpus where they're proven. A profile states facts about how its encoding
encodes; a handshake's facts are the guarantees it establishes.

This renders those facts as tables between the `<!-- encodings:start -->` and
`<!-- encodings:end -->` markers in `docs/docs/reference/wire/official-encodings.md`.
With `--check` it writes nothing and fails if the page differs from what core
says, which is how CI catches drift.

No Rust build: the files are read from a core checkout if one is at hand,
otherwise fetched from GitHub. Stdlib only.

    python3 scripts/sync-official-encodings.py                  # rewrite the page
    python3 scripts/sync-official-encodings.py --check          # fail on drift
    python3 scripts/sync-official-encodings.py --checkout ../core
    python3 scripts/sync-official-encodings.py --rev <sha>
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "docs/docs/reference/wire/official-encodings.md"
RAW = "https://raw.githubusercontent.com/ComlineProject/core"
PACKAGE = "core_stdlib/packages/comline"
START = "<!-- encodings:start -->"
END = "<!-- encodings:end -->"

# `"packed@1" = { kind = "format" profile = "profiles/packed@1.json" ...`
ENTRY_RE = re.compile(
    r'"(?P<name>[^"]+)"\s*=\s*\{\s*kind\s*=\s*"(?P<kind>[a-z]+)"\s*profile\s*=\s*"(?P<profile>[^"]+)"'
)

# The facts each kind of profile states, in the order core lists them
# (`ProfileKind::facts` in core/src/encodings/profile.rs).
FACTS = {
    "format": [
        "struct_fields",
        "unknown_field",
        "missing_optional",
        "enum_variants",
        "unknown_variant",
        "integer_width",
    ],
    "framing": ["calls", "errors"],
    "handshake": ["schema_agreement", "encoding_agreement"],
}


def read(path: str, checkout: Path | None, rev: str) -> str:
    """Read a file of core from a local checkout, else fetch it."""
    if checkout:
        local = checkout / path
        if not local.exists():
            sys.exit(f"error: {local} not found; is --checkout a `core` checkout?")
        return local.read_text(encoding="utf-8")

    url = f"{RAW}/{rev}/{path}"
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            return response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        sys.exit(f"error: fetching {url} failed ({error.code} {error.reason})")
    except urllib.error.URLError as error:
        sys.exit(f"error: fetching {url} failed ({error.reason})")


def encodings(checkout: Path | None, rev: str) -> list[dict]:
    """Every official encoding, in declaration order, with its profile."""
    manifest = read(f"{PACKAGE}/config.idp", checkout, rev)
    found = []
    for match in ENTRY_RE.finditer(manifest):
        profile = json.loads(read(f"{PACKAGE}/{match['profile']}", checkout, rev))
        if profile["name"] != match["name"] or profile["kind"] != match["kind"]:
            sys.exit(f"error: {match['profile']} doesn't describe {match['kind']} `{match['name']}`")
        found.append(profile)
    if not found:
        sys.exit("error: no encodings found in the official package's config.idp")
    return found


def value(fact: dict | None) -> str:
    if fact is None:
        return "not stated"
    v = fact["value"]
    if v is True:
        return "true"
    if v is False:
        return "false"
    return f"`{v}`"


def table(header: list[str], rows: list[list[str]]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return lines


def render(found: list[dict], source: str) -> str:
    out = [
        START,
        f"<!-- Rendered from {source} by scripts/sync-official-encodings.py - don't edit by hand. -->",
        "",
    ]
    for kind, title in [("format", "Formats"), ("framing", "Framings")]:
        of_kind = [p for p in found if p["kind"] == kind]
        out += [f"### {title}", ""]
        out += table(
            [kind] + [f"`{f}`" for f in FACTS[kind]],
            [[f"`{p['name']}`"] + [value(p["facts"].get(f)) for f in FACTS[kind]] for p in of_kind],
        )
        out += [""]

    out += ["### Handshakes", ""]
    rows = []
    for p in (p for p in found if p["kind"] == "handshake"):
        facts = p["facts"]
        establishes = [f.replace("_", " ") for f in FACTS["handshake"] if facts.get(f, {}).get("value") is True]
        rows.append(
            [f"`{p['name']}`"]
            + [value(facts.get(f)) for f in FACTS["handshake"]]
            + [", ".join(establishes) or "nothing"]
        )
    out += table(["handshake"] + [f"`{f}`" for f in FACTS["handshake"]] + ["establishes"], rows)
    out += ["", END]
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="write nothing; fail if the page is out of date")
    parser.add_argument("--checkout", type=Path, help="a local `core` checkout to read instead of fetching")
    # `core`'s default branch is `master`.
    parser.add_argument("--rev", default="master", help="core revision to fetch (default: master)")
    args = parser.parse_args()

    source = "ComlineProject/core's official encodings package"
    rendered = render(encodings(args.checkout, args.rev), source)

    page = PAGE.read_text(encoding="utf-8")
    start, end = page.find(START), page.find(END)
    if start < 0 or end < 0:
        sys.exit(f"error: {PAGE.relative_to(ROOT)} has no {START} ... {END} markers")
    updated = page[:start] + rendered + page[end + len(END):]

    if args.check:
        if updated != page:
            print(f"{PAGE.relative_to(ROOT)} is out of date with core's official encodings;")
            print("regenerate it with `python3 scripts/sync-official-encodings.py`.")
            return 1
        print("The official encodings tables match core.")
        return 0

    PAGE.write_text(updated, encoding="utf-8")
    print(f"wrote {PAGE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
