# Docs

The site is built with [Zensical](https://zensical.org) (the successor to
MkDocs, by the Material for MkDocs team). Configuration still lives in
`mkdocs.yml`, which Zensical reads natively.

## Building

```sh
poetry install                 # Python 3.14+
poetry run zensical serve -o    # live preview at http://localhost:8000
poetry run zensical build       # static output in site/
```

The runtimes' benchmark and fuzzing results on Reference → Languages are
fetched at build time, not committed. Without this first, those sections are
empty:

```sh
python3 ../scripts/sync-language-support.py --render-reports   # writes _generated/ (ignored)
```

`mkdocs` / `mkdocs-material` are kept installed as a fallback during
Zensical's alpha; `poetry run mkdocs serve` still works against the same
`mkdocs.yml`.

## Resource Links
Inspiration for CAS(Content Addressable Storage) 
for Schemas and Project Units; https://git-scm.com/book/en/v2/Git-Internals-Git-Objects


## Drift checks

The CLI reference and the IDL guide are written by hand, in prose deliberately
richer than `--help` text or a token list. Two scripts keep them honest without
generating anything — each only checks that the docs and the source still name
the same things:

```sh
python3 ../scripts/check-cli-drift.py   # needs `comline` on PATH
python3 ../scripts/check-idl-drift.py   # fetches core's grammar; --checkout ../../core to skip
```

`check-cli-drift.py` compares every command and long flag against the installed
binary, both directions. `check-idl-drift.py` compares core's `rust_sitter`
grammar leaves against the IDL guide, counting a keyword as documented when it
appears in a code fence or inline code span.

Both run in CI — IDL drift per relevant PR, CLI drift weekly (it needs a Rust
build, so it is kept off the per-PR path) — and both can be triggered manually
from the Actions tab.
