# Documenting your schemas

`comline doc` turns a package's docs into pages: the `//!` headers of
`config.idp` and of each schema, every declaration's `///` docstring, and what
each protocol resolves to on the wire. Nothing is written by hand, and
everything the package declares is documented.

## 1. Write the docs

Docs live in the schemas, next to what they describe:

- **`///` docstrings** document the declaration below them: a struct, a field,
  an enum, a protocol, a function, an error, a validator, a constant. A
  `/// @name: ...` line documents one field or argument
  ([Docstrings](idl/docstrings.md)).
- **`//!` headers** document a module, at the top of its `.ids` file, and the
  package, at the top of `config.idp`
  ([Module docs](idl/docstrings.md#module-docs)).

```ids linenums="1"
//! The shop's API.

/// One order.
struct Order {
    /// What it costs, in cents.
    total: u64
}

/// Orders things.
protocol Orders {
    /// Place one.
    /// @order: what to place
    function place(order: Order) -> bool;
}
```

The first line of a docstring or header is its summary: index tables show it
next to each name.

## 2. Render them

```bash
comline doc
```

This compiles the working tree and writes Markdown into `docs/api/`:

| File | What's on it |
|---|---|
| `index.md` | The package's name and version, its `config.idp` header, and a table of its modules. |
| `<module>.md` | One per schema (`types::user` is `types/user.md`): its header, a table of what it declares, then each declaration with its docs, annotations, fields, arguments, variants, and each protocol's wire summary, the same table the editor's hover and `comline inspect` show. |
| `changelog.md` | With `--changelog-from`: what changed, as `comline diff` reports it. |
| `nav.yml` | The pages as a `nav` list for mkdocs or zensical. |

Every declaration has an anchor, its name in lowercase (`api.md#order`), and a
type links to the declaration it names, on the same page or another module's.

### Put them on a site

The pages are plain Markdown, so they drop into an mkdocs or zensical site:
render into the site's `docs/` tree and copy `nav.yml`'s entries into
`mkdocs.yml`.

```bash
comline doc --out site/docs/api
```

### Link to dependencies

A type from a dependency or `std` is plain text, unless you say where that
package's docs live. Give each one a base URL in `comline.toml`:

```toml
[doc]
links = { std = "https://example.com/std", billing = "https://docs.example.com/billing" }
```

A type from `billing`'s `api` module, `Invoice`, then links to
`https://docs.example.com/billing/api/#invoice`: the base, the module, and the
anchor, in the directory-URL form mkdocs and zensical publish pages at.

## 3. Document a release

`--version` documents a built version instead of the working tree: a version
string, a commit hash, or `HEAD`.

```bash
comline doc --version 0.2.0 --out site/docs/api/0.2.0
```

A build stores the `//!` headers with the version, so a version documents with
the headers it was built with, even after the sources change. Two things need
the source and are missing from a built version: protocols have no wire
summary, and dependency types have no link. A version built before headers
were stored has none.

`--changelog-from` adds what changed since an earlier built version:

```bash
comline doc --version 0.2.0 --changelog-from 0.1.0
```

## 4. Or take the model

`--format json` writes the documentation model itself, `model.json`: the same
data the pages are rendered from, as JSON. Its shape is a published schema,
[`doc-model/1.json`](../schemas/doc-model/1.json), so a tool of your own can
render it any way it likes.

```bash
comline doc --format json
```

A renderer of your own can also run inside `comline doc`: a program speaking
the [generator protocol](../reference/generator-protocol.md#render) that answers
`Render` requests, named by `[doc] renderer` in `comline.toml`. It runs exactly
like an [external generator](extending/generators.md): a `.wasm` is sandboxed,
and every path it returns is checked before anything is written.

## Settings

Every flag has a `[doc]` key in [`comline.toml`](../reference/congregation/comline-toml.md#doc),
and the flag wins:

| Key | Flag | Default |
|---|---|---|
| `out` | `--out` | `docs/api` |
| `format` | `--format` | `markdown` |
| `changelog_from` | `--changelog-from` | none |
| `renderer`, `timeout` | none | the built-in renderer |
| `links` | none | none |

## The standard library, rendered

The standard library is rendered this way, and is the live example: the
[`std` pages](../std/index.md) are `comline doc` run over std's own package,
with nothing written by hand. A type from `std` in your own docs links to them
with `links = { std = "https://comlineproject.github.io/docs/std" }`, so
`std::http::Request` in a field's type links to
`https://comlineproject.github.io/docs/std/http/#request`.
