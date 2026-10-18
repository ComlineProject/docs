#!/usr/bin/env python3
"""Keep the Reference → Languages pages in step with what conformance proved.

Two conformance suites feed the pages:

- `ComlineProject/generation`'s checks every code generator's feature claims
  and writes `features.json` at its root;
- `ComlineProject/runtime`'s wire corpus (`runtime/conformance/`) checks every
  runtime's claims; each runtime writes a report (see `RUNTIMES`).

This renders, on `reference/languages/`:

- `index.md`: the code generation matrix (`<!-- matrix:start -->` ...
  `<!-- matrix:end -->`) and the runtime matrix (`runtime-matrix`);
- `<name>.md`: that language's code generation table (`codegen`) and runtime
  table (`runtime`).

Issue references (`core#96`) become links. A generator or runtime with no page
of its own is an error that names the page to add.

    python3 scripts/sync-language-support.py            # rewrite the pages
    python3 scripts/sync-language-support.py --check    # exit 1 on drift
    python3 scripts/sync-language-support.py --file ../generation/features.json \\
        --runtime-features ../runtime/runtime/conformance/features.json \\
        --runtime-report rust=../runtime/runtime/conformance/reports/rust.json

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
RAW = "https://raw.githubusercontent.com/ComlineProject/{repo}/{rev}/{path}"
NOTICE = (
    "<!-- Rendered from ComlineProject/generation's features.json by "
    "scripts/sync-language-support.py - don't edit by hand. -->"
)
RUNTIME_NOTICE = (
    "<!-- Rendered from ComlineProject/runtime's conformance corpus and each runtime's report by "
    "scripts/sync-language-support.py - don't edit by hand. -->"
)

# The wire corpus, and where each language's runtime writes its report:
# (repository, path in it).
CORPUS = ("runtime", "runtime/conformance/features.json")
VECTORS = "https://github.com/ComlineProject/runtime/blob/main/runtime/conformance/vectors/{id}.json"
RUNTIMES = {
    "rust": ("runtime", "runtime/conformance/reports/rust.json"),
    "typescript": ("comline-typescript", "runtime/conformance-report.json"),
}

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


def read_json(file: Path | None, repo: str, rev: str, path: str) -> dict:
    if file:
        return json.loads(file.read_text(encoding="utf-8"))
    url = RAW.format(repo=repo, rev=rev, path=path)
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


def runtime_state(claim: dict) -> str:
    out = state_with_detail(claim)
    if claim.get("failing"):
        out += " <br>fails: " + ", ".join(f"`{case}`" for case in claim["failing"])
    return out


def runtime_proof(feature: str, claim: dict) -> str:
    n = len(claim.get("proven_by") or [])
    if not n:
        return "—"
    return f"[{n} case{'s' if n != 1 else ''}]({VECTORS.format(id=feature)})"


def runtime_matrix(corpus: dict, reports: dict[str, dict]) -> str:
    lines = ["| Feature | " + " | ".join(f"[{name}]({name}.md#runtime)" for name in reports) + " |"]
    lines.append("|---|" + "---|" * len(reports))
    for feature in corpus["features"]:
        row = [f"{feature['title']} <br><sub>`{feature['id']}`</sub>"]
        row += [state_with_detail(report["support"][feature["id"]]) for report in reports.values()]
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def runtime_table(corpus: dict, report: dict) -> str:
    lines = [
        f"Runtime `{report['runtime']}`.",
        "",
        "| Feature | What it covers | State | Proven by |",
        "|---|---|---|---|",
    ]
    for feature in corpus["features"]:
        claim = report["support"][feature["id"]]
        lines.append(
            f"| {feature['title']} <br><sub>`{feature['id']}`</sub> | {cell(feature['description'])} "
            f"| {runtime_state(claim)} | {runtime_proof(feature['id'], claim)} |"
        )
    return "\n".join(lines)


def replace_section(text: str, page: Path, name: str, body: str, notice: str = NOTICE) -> str:
    """`text` of `page` with its `name` section set to `body`."""
    start, end = f"<!-- {name}:start -->", f"<!-- {name}:end -->"
    i, j = text.find(start), text.find(end)
    if i < 0 or j < 0:
        sys.exit(f"error: {page.relative_to(ROOT)} has no {start} ... {end} section")
    return text[:i] + f"{start}\n{notice}\n\n{body}\n\n{end}" + text[j + len(end) :]


def page_for(name: str, section: str, what: str) -> Path:
    page = PAGES / f"{name}.md"
    if not page.exists():
        sys.exit(
            f"error: {what} `{name}` has no page - add {page.relative_to(ROOT)} "
            f"with a `<!-- {section}:start -->` / `<!-- {section}:end -->` section, and list it in mkdocs.yml"
        )
    return page


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="exit 1 if a page is out of date")
    parser.add_argument("--file", type=Path, help="read generation's features.json from here instead of fetching it")
    parser.add_argument("--rev", default="master", help="generation revision to fetch (default: master)")
    parser.add_argument("--runtime-features", type=Path, help="read the wire corpus's features.json from here")
    parser.add_argument(
        "--runtime-report",
        action="append",
        default=[],
        metavar="NAME=FILE",
        help="read runtime NAME's conformance report from FILE (repeatable)",
    )
    parser.add_argument("--runtime-rev", default="main", help="revision of the runtime repositories to fetch (default: main)")
    args = parser.parse_args()

    local_reports = dict(arg.split("=", 1) for arg in args.runtime_report)
    for name in local_reports:
        if name not in RUNTIMES:
            sys.exit(f"error: unknown runtime `{name}` (known: {', '.join(RUNTIMES)})")

    report = read_json(args.file, "generation", args.rev, "features.json")
    corpus = read_json(args.runtime_features, CORPUS[0], args.runtime_rev, CORPUS[1])
    runtimes = {
        name: read_json(Path(local_reports[name]) if name in local_reports else None, repo, args.runtime_rev, path)
        for name, (repo, path) in RUNTIMES.items()
    }

    # Every page's wanted text, starting from what's on disk; a page gets
    # its code generation and runtime sections in turn.
    wanted: dict[Path, str] = {}

    def update(page: Path, section: str, body: str, notice: str = NOTICE) -> None:
        text = wanted.get(page) or page.read_text(encoding="utf-8")
        wanted[page] = replace_section(text, page, section, body, notice)

    index = PAGES / "index.md"
    update(index, "matrix", matrix(report))
    update(index, "runtime-matrix", runtime_matrix(corpus, runtimes), RUNTIME_NOTICE)
    for generator in report["generators"]:
        update(page_for(generator["name"], "codegen", "generator"), "codegen", language_table(report, generator))
    for name, runtime in runtimes.items():
        update(page_for(name, "runtime", "runtime"), "runtime", runtime_table(corpus, runtime), RUNTIME_NOTICE)

    stale = [(page, text) for page, text in wanted.items() if page.read_text(encoding="utf-8") != text]
    if not stale:
        print("language reference pages are up to date")
        return 0
    if args.check:
        for page, _ in stale:
            print(f"{page.relative_to(ROOT)} is out of date with the conformance results.")
        print("Run: python3 scripts/sync-language-support.py")
        return 1
    for page, text in stale:
        page.write_text(text, encoding="utf-8")
        print(f"updated {page.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
