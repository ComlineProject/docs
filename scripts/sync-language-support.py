#!/usr/bin/env python3
"""Keep the Reference → Languages pages in step with what conformance proved.

`ComlineProject/generation`'s conformance suite checks every generator's
feature claims against its corpus and writes the result to `features.json` at
the repository root. This renders, from that file:

- the cross-language matrix on `reference/languages/index.md`, between
  `<!-- matrix:start -->` / `<!-- matrix:end -->`;
- each language's own table on `reference/languages/<name>.md`, between
  `<!-- codegen:start -->` / `<!-- codegen:end -->`.

Issue references (`core#96`) become links. A generator with no page of its
own is an error that names the page to add.

    python3 scripts/sync-language-support.py            # rewrite the pages
    python3 scripts/sync-language-support.py --check    # exit 1 on drift
    python3 scripts/sync-language-support.py --file ../generation/features.json

Stdlib only: no Rust toolchain needed, so CI runs it per pull request.
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
PAGES = ROOT / "docs/docs/reference/languages"
RAW = "https://raw.githubusercontent.com/ComlineProject/generation/{rev}/features.json"
NOTICE = (
    "<!-- Rendered from ComlineProject/generation's features.json by "
    "scripts/sync-language-support.py - don't edit by hand. -->"
)

# Repositories an issue reference may name; anything else is left as text
# (`rust#1.70.0` is a target, not an issue).
REPOS = ("core", "generation", "cli", "comline-rust", "comline-typescript", "language-server", "runtime", "docs")
ISSUE_RE = re.compile(r"\b(" + "|".join(re.escape(r) for r in REPOS) + r")#(\d+)\b(?![\d.])")

STATES = {
    "supported": "✅ supported",
    "partial": "🟡 partial",
    "ignored": "⚪ ignored",
    "unsupported": "❌ unsupported",
}


def read_report(file: Path | None, rev: str) -> dict:
    if file:
        return json.loads(file.read_text(encoding="utf-8"))
    url = RAW.format(rev=rev)
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        sys.exit(f"error: fetching {url} failed ({error.code} {error.reason})")
    except urllib.error.URLError as error:
        sys.exit(f"error: fetching {url} failed ({error.reason})")


def link_issues(text: str) -> str:
    return ISSUE_RE.sub(lambda m: f"[{m[0]}](https://github.com/ComlineProject/{m[1]}/issues/{m[2]})", text)


def cell(text: str) -> str:
    return link_issues(text).replace("|", "\\|")


def state_with_detail(claim: dict) -> str:
    out = STATES[claim["state"]]
    if claim.get("note"):
        out += f": {claim['note']}"
    if claim.get("tracking"):
        out += f" ({claim['tracking']})"
    return cell(out)


def proof(claim: dict) -> str:
    return ", ".join(f"`{fixture}`" for fixture in claim.get("proven_by") or []) or "—"


def matrix(report: dict) -> str:
    generators = report["generators"]
    lines = ["| Feature | " + " | ".join(f"[{g['name']} {g['version']}]({g['name']}.md)" for g in generators) + " |"]
    lines.append("|---|" + "---|" * len(generators))
    for feature in report["features"]:
        row = [f"{feature['title']} <br><sub>`{feature['id']}`</sub>"]
        row += [state_with_detail(g["support"][feature["id"]]) for g in generators]
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def language_table(report: dict, generator: dict) -> str:
    lines = [
        f"Generator `{generator['name']}#{generator['version']}`.",
        "",
        "| Feature | What it covers | State | Proven by |",
        "|---|---|---|---|",
    ]
    for feature in report["features"]:
        claim = generator["support"][feature["id"]]
        lines.append(
            f"| {feature['title']} <br><sub>`{feature['id']}`</sub> | {cell(feature['description'])} "
            f"| {state_with_detail(claim)} | {proof(claim)} |"
        )
    return "\n".join(lines)


def replace_section(page: Path, name: str, body: str) -> tuple[str, str]:
    """`(current, wanted)` text of `page` with its `name` section set to `body`."""
    text = page.read_text(encoding="utf-8")
    start, end = f"<!-- {name}:start -->", f"<!-- {name}:end -->"
    i, j = text.find(start), text.find(end)
    if i < 0 or j < 0:
        sys.exit(f"error: {page.relative_to(ROOT)} has no {start} ... {end} section")
    return text, text[:i] + f"{start}\n{NOTICE}\n\n{body}\n\n{end}" + text[j + len(end) :]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="exit 1 if a page is out of date")
    parser.add_argument("--file", type=Path, help="read features.json from here instead of fetching it")
    parser.add_argument("--rev", default="master", help="generation revision to fetch (default: master)")
    args = parser.parse_args()

    report = read_report(args.file, args.rev)
    changes: list[tuple[Path, str, str]] = [(PAGES / "index.md", *replace_section(PAGES / "index.md", "matrix", matrix(report)))]
    for generator in report["generators"]:
        page = PAGES / f"{generator['name']}.md"
        if not page.exists():
            sys.exit(
                f"error: generator `{generator['name']}` has no page - add {page.relative_to(ROOT)} "
                "with a `<!-- codegen:start -->` / `<!-- codegen:end -->` section, and list it in mkdocs.yml"
            )
        # A page's earlier sections are already in `current` for a second one.
        current, wanted = replace_section(page, "codegen", language_table(report, generator))
        changes.append((page, current, wanted))

    stale = [(page, wanted) for page, current, wanted in changes if current != wanted]
    if not stale:
        print("language reference pages are up to date")
        return 0
    if args.check:
        for page, _ in stale:
            print(f"{page.relative_to(ROOT)} is out of date with generation's features.json.")
        print("Run: python3 scripts/sync-language-support.py")
        return 1
    for page, wanted in stale:
        page.write_text(wanted, encoding="utf-8")
        print(f"updated {page.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
