#!/usr/bin/env python3
"""Keep the served `comline.toml` JSON Schema equal to generation's.

`comline_codegen::config` is the source of truth: generation derives
`schemas/comline-toml.json` from it and drift-checks that file there. This repo
only serves a copy, at `/schemas/comline-toml/0.x.json`, because `comline new`
writes that URL into a fresh `comline.toml` as a `#:schema` line.

    python3 scripts/sync-comline-toml-schema.py           # check; exit 1 on drift
    python3 scripts/sync-comline-toml-schema.py --write   # refresh the copy
    python3 scripts/sync-comline-toml-schema.py --rev <sha>

The schema is fetched from generation's default branch (`HEAD`) unless pinned.
"""

from __future__ import annotations

import argparse
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COPY = ROOT / "docs/docs/schemas/comline-toml/0.x.json"
RAW = "https://raw.githubusercontent.com/ComlineProject/generation/{rev}/schemas/comline-toml.json"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--write", action="store_true", help="overwrite the committed copy")
    ap.add_argument("--rev", default="HEAD", help="generation ref to read (default: HEAD)")
    args = ap.parse_args()

    url = RAW.format(rev=args.rev)
    with urllib.request.urlopen(url, timeout=30) as r:
        upstream = r.read()

    if args.write:
        COPY.write_bytes(upstream)
        print(f"wrote {COPY.relative_to(ROOT)} from {url}")
        return 0

    if COPY.read_bytes() == upstream:
        print("comline.toml schema: up to date")
        return 0

    print(f"{COPY.relative_to(ROOT)} differs from generation's schemas/comline-toml.json")
    print("Refresh it with:")
    print("    python3 scripts/sync-comline-toml-schema.py --write")
    return 1


if __name__ == "__main__":
    sys.exit(main())
