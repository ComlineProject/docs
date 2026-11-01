#!/usr/bin/env python3
"""Keep the served JSON Schemas equal to their sources.

- `comline.toml`: `comline_codegen::config` is the source of truth; generation
  derives `schemas/comline-toml.json` from it and drift-checks that file there.
  This repo serves a copy at `/schemas/comline-toml/0.x.json`, because
  `comline new` writes that URL into a fresh `comline.toml` as a `#:schema`
  line.
- The documentation model: core's `comline_core::doc` derives
  `schemas/doc-model.json` (its `$id` is this site's
  `/schemas/doc-model/1.json`) and drift-checks it there. This repo serves the
  copy renderers validate against. The `1` is `DOC_MODEL_VERSION`: a new model
  version is a new file, and the old ones stay.

    python3 scripts/sync-comline-toml-schema.py           # check; exit 1 on drift
    python3 scripts/sync-comline-toml-schema.py --write   # refresh the copies
    python3 scripts/sync-comline-toml-schema.py --rev <sha> --core-rev <sha>

Each schema is fetched from its repo's default branch (`HEAD`) unless pinned.
"""

from __future__ import annotations

import argparse
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# (served copy, source URL template, which `--...rev` pins it)
SCHEMAS = [
    (
        ROOT / "docs/docs/schemas/comline-toml/0.x.json",
        "https://raw.githubusercontent.com/ComlineProject/generation/{rev}/schemas/comline-toml.json",
        "rev",
    ),
    (
        ROOT / "docs/docs/schemas/doc-model/1.json",
        "https://raw.githubusercontent.com/ComlineProject/core/{rev}/schemas/doc-model.json",
        "core_rev",
    ),
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--write", action="store_true", help="overwrite the committed copy")
    ap.add_argument("--rev", default="HEAD", help="generation ref to read (default: HEAD)")
    ap.add_argument("--core-rev", default="HEAD", help="core ref to read (default: HEAD)")
    args = ap.parse_args()

    drifted = False
    for copy, raw, pin in SCHEMAS:
        url = raw.format(rev=getattr(args, pin))
        with urllib.request.urlopen(url, timeout=30) as r:
            upstream = r.read()
        name = copy.relative_to(ROOT)

        if args.write:
            copy.parent.mkdir(parents=True, exist_ok=True)
            copy.write_bytes(upstream)
            print(f"wrote {name} from {url}")
        elif copy.exists() and copy.read_bytes() == upstream:
            print(f"{name}: up to date")
        else:
            print(f"{name} differs from {url}")
            drifted = True

    if drifted:
        print("Refresh with:")
        print("    python3 scripts/sync-comline-toml-schema.py --write")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
