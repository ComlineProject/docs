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

`mkdocs` / `mkdocs-material` are kept installed as a fallback during
Zensical's alpha; `poetry run mkdocs serve` still works against the same
`mkdocs.yml`.

## Resource Links
Inspiration for CAS(Content Addressable Storage) 
for Schemas and Project Units; https://git-scm.com/book/en/v2/Git-Internals-Git-Objects

