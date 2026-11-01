#!/usr/bin/env python3
"""Render the standard library's pages with `comline doc`.

`std` is the package embedded in core, at `core_stdlib/packages/std/`. Its
`//!` headers and `///` docstrings are the documentation; `comline doc` turns
them into the pages under `docs/docs/std/`, and their `nav` into the block
between the `std:start` and `std:end` markers in `docs/mkdocs.yml`. Nothing
under `docs/docs/std/` is written by hand: edit std's docstrings in core and
re-run this.

Other docs link here (`https://comlineproject.github.io/docs/std/http/#httpmethod`
is what `[doc] links = { std = ... }` produces), so the pages' paths are part
of the site's contract: `std/<module>.md` publishes at `/std/<module>/`.

Needs `comline` on PATH (or `--comline`) and `git` when no `--checkout` is
given. The docs CI has no Rust toolchain by default, so the drift workflow
installs the CLI first, like the CLI drift check.

    python3 scripts/sync-std-docs.py                  # rewrite the pages and nav
    python3 scripts/sync-std-docs.py --check          # fail on drift
    python3 scripts/sync-std-docs.py --checkout ../core
    python3 scripts/sync-std-docs.py --rev <sha>
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES = ROOT / "docs/docs/std"
MKDOCS = ROOT / "docs/mkdocs.yml"
CORE = "https://github.com/ComlineProject/core"
PACKAGE = "core_stdlib/packages/std"
START = "# std:start"
END = "# std:end"
# Where the block sits in mkdocs.yml, so its entries are indented to match.
INDENT = "    "

# `  - "http": http.md`
NAV_RE = re.compile(r'^\s*-\s*"(?P<title>[^"]+)":\s*(?P<path>\S+)\s*$')


def fetch_core(rev: str | None, into: Path) -> Path:
    """Shallow-clone core (its default branch, or `rev`) into `into`."""
    if rev:
        subprocess.run(["git", "init", "-q", str(into)], check=True)
        subprocess.run(["git", "-C", str(into), "fetch", "-q", "--depth", "1", CORE, rev], check=True)
        subprocess.run(["git", "-C", str(into), "checkout", "-q", "FETCH_HEAD"], check=True)
    else:
        subprocess.run(["git", "clone", "-q", "--depth", "1", CORE, str(into)], check=True)
    return into


def document(comline: str, package: Path, out: Path) -> None:
    """`comline doc` over std's package directory, into `out`."""
    result = subprocess.run(
        [comline, "--plain", "--path", str(package), "doc", "--out", str(out)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        sys.exit(f"error: `comline doc` failed:\n{result.stdout}{result.stderr}")


def nav_block(nav_yml: Path) -> str:
    """The generated `nav.yml` as the marked block of mkdocs.yml."""
    lines = [f"{INDENT}{START}", f"{INDENT}- Standard library:"]
    for line in nav_yml.read_text(encoding="utf-8").splitlines():
        match = NAV_RE.match(line)
        if match:
            lines.append(f"{INDENT}  - {match['title']}: 'std/{match['path']}'")
    lines.append(f"{INDENT}{END}")
    return "\n".join(lines)


def splice(mkdocs: str, block: str) -> str:
    start, end = mkdocs.find(f"{INDENT}{START}"), mkdocs.find(END)
    if start < 0 or end < 0:
        sys.exit(f"error: {MKDOCS.relative_to(ROOT)} has no `{START}` ... `{END}` markers")
    return mkdocs[:start] + block + mkdocs[end + len(END):]


def pages(directory: Path) -> dict[str, bytes]:
    return {p.name: p.read_bytes() for p in sorted(directory.glob("*.md"))}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="write nothing; fail if the pages or nav are out of date")
    parser.add_argument("--checkout", type=Path, help="a local `core` checkout to read instead of cloning")
    parser.add_argument("--rev", help="core revision to clone (default: the default branch)")
    parser.add_argument("--comline", default="comline", help="the `comline` binary (default: from PATH)")
    args = parser.parse_args()

    if not shutil.which(args.comline):
        sys.exit(f"error: `{args.comline}` not found; install the CLI or pass --comline")

    with tempfile.TemporaryDirectory(prefix="std-docs-") as tmp:
        tmp = Path(tmp)
        core = args.checkout or fetch_core(args.rev, tmp / "core")
        package = core / PACKAGE
        if not (package / "config.idp").exists():
            sys.exit(f"error: {package} is not std's package; is --checkout a `core` checkout?")

        out = tmp / "out"
        document(args.comline, package, out)
        # A `comline doc` that documents every version (generation#101)
        # writes `<out>/markdown/<version>/`; std is never built, so its one
        # version is the working tree, `unreleased`.
        if (out / "markdown").is_dir():
            out = out / "markdown" / "unreleased"

        generated = pages(out)
        block = nav_block(out / "nav.yml")
        mkdocs = MKDOCS.read_text(encoding="utf-8")
        updated = splice(mkdocs, block)
        current = pages(PAGES) if PAGES.exists() else {}

        if args.check:
            problems = []
            for name in sorted(generated.keys() | current.keys()):
                if name not in current:
                    problems.append(f"missing: std/{name}")
                elif name not in generated:
                    problems.append(f"stale: std/{name} (std no longer has it)")
                elif generated[name] != current[name]:
                    problems.append(f"changed: std/{name}")
            if updated != mkdocs:
                problems.append(f"changed: the std nav in {MKDOCS.relative_to(ROOT)}")
            if problems:
                print("The standard library pages are out of date with core's std package:")
                for problem in problems:
                    print(f"  {problem}")
                print("regenerate them with `python3 scripts/sync-std-docs.py`.")
                return 1
            print("The standard library pages match core.")
            return 0

        PAGES.mkdir(parents=True, exist_ok=True)
        for stale in set(current) - set(generated):
            (PAGES / stale).unlink()
        for name, contents in generated.items():
            (PAGES / name).write_bytes(contents)
        MKDOCS.write_text(updated, encoding="utf-8")
        print(f"wrote {len(generated)} page(s) to {PAGES.relative_to(ROOT)} and the nav in {MKDOCS.relative_to(ROOT)}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
