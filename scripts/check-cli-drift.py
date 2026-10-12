#!/usr/bin/env python3
"""Compare the documented CLI surface against the real one.

`docs/docs/reference/cli.md` describes every command and flag by hand, and the
prose there is deliberately richer than clap's one-line help strings — so this
does *not* generate the page. It only checks that the page mentions every
command and flag the binary actually has, and nothing it doesn't: the failure
mode worth catching is a flag landing in the CLI and never reaching the docs.

Needs `comline` on PATH. The docs CI has no Rust toolchain, so this runs
locally or in a job that installs the CLI first.

    python3 scripts/check-cli-drift.py            # check, exit 1 on drift
    python3 scripts/check-cli-drift.py --verbose  # also list what matched

Flags every command inherits (`--path`, `--verbose`, `--quiet`, `--plain`) are
documented once in their own table rather than repeated per command, so they
are checked once globally and ignored per command. `--help` / `--version` are
clap's own and never documented.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS_PAGE = ROOT / "docs/docs/reference/cli.md"
# The page's tables may be assembled at build time from `_data/*.yaml` by the
# macros extension, so the documented surface is the page *plus* that data.
DATA_DIR = ROOT / "docs/_data"

# Inherited by every subcommand; documented once under "Global flags".
GLOBAL_FLAGS = {"--path", "--verbose", "--quiet", "--plain"}
# clap's own, never documented.
IGNORED_FLAGS = {"--help", "--version"}
# Real commands that are not part of the documented surface.
IGNORED_COMMANDS = {"help"}

FLAG_RE = re.compile(r"--[a-z][a-z0-9-]*")


def run_help(args: list[str]) -> str:
    """Capture `comline <args> --help`."""
    result = subprocess.run(
        ["comline", *args, "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        sys.exit(f"error: `comline {' '.join(args)} --help` failed:\n{result.stderr}")
    return result.stdout


def parse_commands(help_text: str) -> set[str]:
    """Pull command names out of the top-level help's `Commands:` block."""
    commands = set()
    in_block = False
    for line in help_text.splitlines():
        if line.startswith("Commands:"):
            in_block = True
            continue
        if in_block:
            # The block ends at the next unindented line (e.g. `Options:`).
            if line.strip() and not line.startswith(" "):
                break
            if match := re.match(r"\s+([a-z][a-z0-9-]*)\s{2,}\S", line):
                commands.add(match.group(1))
    return commands - IGNORED_COMMANDS


def parse_flags(help_text: str) -> set[str]:
    """Pull long flags out of a help text's `Options:` block."""
    flags = set()
    in_block = False
    for line in help_text.splitlines():
        if line.startswith("Options:"):
            in_block = True
            continue
        if in_block:
            if line.strip() and not line.startswith(" "):
                break
            # Only the flag declaration itself is indented two spaces; wrapped
            # description lines are indented much further, and may contain
            # `--flag` references that are not this command's own flags.
            if re.match(r"\s{2,8}-", line):
                flags.update(FLAG_RE.findall(line))
    return flags - IGNORED_FLAGS


def documented(page: str) -> tuple[set[str], set[str]]:
    """Extract the commands and flags the docs mention."""
    commands = set(re.findall(r"`comline ([a-z][a-z0-9-]*)", page))
    # Flags written as `--flag` anywhere on the page, including inside the
    # command table's usage column and the Global flags table.
    flags = set(FLAG_RE.findall(page))
    return commands, flags


def report(label: str, missing: set[str], extra: set[str]) -> bool:
    """Print one section. Returns True if it found drift."""
    if not missing and not extra:
        return False
    print(f"\n{label}")
    for item in sorted(missing):
        print(f"  + {item:<20} in the CLI, not in the docs")
    for item in sorted(extra):
        print(f"  - {item:<20} in the docs, not in the CLI")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--verbose", action="store_true", help="also list what matched"
    )
    args = parser.parse_args()

    if not shutil.which("comline"):
        sys.exit(
            "error: `comline` is not on PATH.\n"
            "       Install it with `cargo install --path .` from a checkout of\n"
            "       https://github.com/ComlineProject/cli"
        )
    if not DOCS_PAGE.exists():
        sys.exit(f"error: {DOCS_PAGE} not found")

    sources = [DOCS_PAGE.read_text(encoding="utf-8")]
    if DATA_DIR.is_dir():
        sources += [
            f.read_text(encoding="utf-8") for f in sorted(DATA_DIR.glob("*.yaml"))
        ]
    doc_commands, doc_flags = documented("\n".join(sources))

    root_help = run_help([])
    real_commands = parse_commands(root_help)
    real_globals = parse_flags(root_help) & GLOBAL_FLAGS

    drift = False
    drift |= report(
        "Commands", real_commands - doc_commands, doc_commands - real_commands
    )
    drift |= report("Global flags", real_globals - doc_flags, set())

    all_real_flags = set(real_globals) | IGNORED_FLAGS
    for command in sorted(real_commands):
        own = parse_flags(run_help([command])) - GLOBAL_FLAGS
        all_real_flags |= own
        # A flag absent from the whole page is undocumented. Checking
        # page-wide rather than per-row keeps prose that explains a flag in a
        # paragraph instead of the table from reading as drift.
        drift |= report(f"`comline {command}`", own - doc_flags, set())
        if args.verbose and own:
            print(f"\n`comline {command}` documented: {', '.join(sorted(own & doc_flags))}")

    # The other direction, checked once against the union: a flag the docs
    # still describe after the CLI dropped or renamed it. Per-command this
    # would misfire, since flags are matched page-wide.
    drift |= report("Documented but gone", set(), doc_flags - all_real_flags)

    if drift:
        print(f"\nDrift found. Update {DOCS_PAGE.relative_to(Path.cwd())}.")
        return 1

    version = subprocess.run(
        ["comline", "--version"], capture_output=True, text=True, check=False
    ).stdout.split("\n")[0]
    print(f"No drift: the docs match {version}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
