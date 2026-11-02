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

This documents every version of the package: each release, each dev build,
and the working tree's unreleased changes. Each one is written as Markdown into
its own folder under `docs/api/markdown/`:

```text
docs/api/markdown/
├── index.md        # the versions, grouped by release
├── 0.1.0/
├── 0.2.0-dev.1/    # a dev build, listed under the release it leads to
├── 0.2.0/
└── unreleased/     # the working tree, when it differs from the last build
```

Before the first `comline build`, `unreleased/` is the only version. Each
version's folder has these pages:

| File | What's on it |
|---|---|
| `index.md` | The package's name and version, its `config.idp` header, a table of its modules, and a table of its dependencies. |
| `<module>.md` | One per schema (`types::user` is `types/user.md`): its header, a table of what it declares, then each declaration with its docs, annotations, fields, arguments, variants, and each protocol's wire summary, the same table the editor's hover and `comline inspect` show. |
| `changelog.md` | What changed, as `comline diff` reports it: each change's severity and a short title, then the old and new IDL lines as a `diff` block. A release shows everything since the previous release; a dev build what changed since the build before it, with a link to everything since the last release. |
| `nav.yml` | The pages as a `nav` list for mkdocs or zensical. |

Every declaration has an anchor, its name in lowercase (`api.md#order`), and a
type links to the declaration it names, on the same page or another module's.

Run it again and only what changed is rendered again. A built version never
changes, so its folder is kept: `docs/api/markdown/.comline-doc.json` records
what each folder was rendered from. Usually only `unreleased/` and any new
version are rendered.

To look at the result, `comline doc open` opens it (the HTML site if you
render one, else the first format you configured), rendering it first when
there is nothing to open; `comline doc --open` renders, then opens. HTML opens
in the browser `$BROWSER` names, else your default one. See
[comline doc](../reference/tools/doc.md#opening-the-result).

### Put them on a site

The pages are plain Markdown, so they drop into an mkdocs or zensical site:
render into the site's `docs/` tree and copy a version's `nav.yml` entries into
`mkdocs.yml`.

```bash
comline doc --out site/docs/api
```

The Markdown output has no version picker. To publish several versions, use
your site tool's versioning. With mkdocs, [mike](https://github.com/jimporter/mike)
deploys each version folder as a version of the site and adds a selector. To
publish only the latest version, trim the list with `[doc] versions` (see
[Choose the versions](#3-choose-the-versions)).

### Or as a site of its own

`--format html` writes a finished static site instead, with the same content
as the Markdown pages:

```bash
comline doc --format html --out site
```

Open `site/html/index.html` straight from disk, or put the folder on any static
host. It opens the latest version: the newest release, or the newest dev build
before the first release.

- **Each page** has a sidebar of your modules and their declarations, then a
  collapsed Dependencies section, and a search box over every declaration. The theme follows the OS's light or dark setting
  until you pick one with the toggle in the header, which the site remembers.
- **The version picker** in the header switches versions and keeps your place:
  the same page and declaration in the chosen version, or that version's
  overview, with a note, when it doesn't have them. Dev builds are grouped under
  the release they lead to.
- **Compare** (in the header, or `site/html/compare.html`) shows how versions
  differ. Tick two to see what changed between them, grouped by declaration and
  labelled major, minor or patch. Tick more to see a grid of every declaration
  and member, with its type or signature in each version. The labels are the
  same ones `comline diff` gives, computed when the docs are rendered.

Nothing loads from the network: the stylesheet, the search index and the
version data are files in the folder, and every link is relative. To make HTML
the default, or to write several formats in one run, list them under `[doc]` in
`comline.toml`:

```toml
[doc]
formats = ["html", "markdown"]
```

The site is generated, so a new project's `.gitignore` (from `comline new`)
leaves out `docs/api/html/`.

### Dependencies

Your docs document your package. What it uses of each dependency, and of
`std`, is listed apart, under Dependencies in the sidebar and the index: only
the declarations your own use, and what those use in turn, never the whole
dependency. Each dependency gets its own pages (`deps/<package>/<module>`), and
a type from it links there.

`std` links to its hosted docs instead, `https://comlineproject.github.io/docs/std/`.
To link another dependency to its published docs rather than render pages for
it, give it a base URL in `comline.toml`:

```toml
[doc]
links = { std = "https://example.com/std", billing = "https://docs.example.com/billing" }
```

A type from `billing`'s `api` module, `Invoice`, then links to
`https://docs.example.com/billing/api/#invoice`: the base, the module, and the
anchor, in the directory-URL form mkdocs and zensical publish pages at. A
`links` entry for `std` replaces its default.

## 3. Choose the versions

Every version is documented by default. `[doc] versions` trims the list:

```toml
[doc]
versions = { last = 5 }              # the newest five
# versions = { since = "0.3.0" }     # 0.3.0 and newer
# versions = { releases_only = true } # releases only: no dev builds, no unreleased state
```

The keys combine: `{ releases_only = true, last = 3 }` is the last three
releases. A version that's trimmed away has its folder removed on the next run.

`--version` documents one built version on its own, into its folder: a version
string, a commit hash, or `HEAD`.

```bash
comline doc --version 0.2.0
```

`--changelog-from` adds what changed since an earlier built version to it:

```bash
comline doc --version 0.2.0 --changelog-from 0.1.0
```

A build stores the `//!` headers with the version, so a version documents with
the headers it was built with, even after the sources change. One thing needs
the source: protocols in a built version have no wire summary. A version built
before headers were stored has no headers. Its pages open with a note saying what's missing.

## 4. Or take the model

`--format json` writes the documentation model itself, each version's
`model.json`, with `docs/api/json/index.json` listing the versions: the same
data the pages are rendered from, as JSON. Its shape is a published schema,
[`doc-model/1.json`](../schemas/doc-model/1.json), so a tool of your own can
render it any way it likes. The schema grows without a version bump when
something is added, so skip any `kind` you don't know.

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
| `formats` | `--format` | `["markdown"]` |
| `versions` | `--version` (one version) | `"all"` |
| `changelog_from` | `--changelog-from` | none; with `--version` only |
| `renderer`, `timeout` | none | the built-in renderer |
| `links` | none | none |

## The standard library, rendered

The standard library is rendered this way, and is the live example: the
[`std` pages](../std/index.md) are `comline doc` run over std's own package,
with nothing written by hand. They use the Markdown format, so they become
pages of this site rather than a separate one. A type from `std` in your own
docs links to them by default, so `std::http::Request` in a field's type links
to `https://comlineproject.github.io/docs/std/http/#request`.
