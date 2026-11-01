# comline doc

```
comline doc [--out <dir>] [--version <v>] [--changelog-from <v>] [--format markdown|html|json]
```

`comline doc` writes a package's documentation. Like `comline check`, it writes
nothing to `.comline/`. For a walkthrough, see
[Documenting your schemas](../../guide/documenting.md).

## Flags

| Flag | Default | Meaning |
|---|---|---|
| `--out <dir>` | `[doc] out`, else `docs/api` | Where to write, relative to the project. |
| `--version <v>` | the working tree | Document a built version: a version string, a commit hash (4+ characters), or `HEAD`. |
| `--changelog-from <v>` | `[doc] changelog_from` | Add what changed from built version `<v>` to the documented one. |
| `--format <f>` | `[doc] format`, else `markdown` | `markdown`, `html`, `json`, or another renderer id `[doc] renderer` offers. |

The `[doc]` keys are in [`comline.toml`](../congregation/comline-toml.md#doc).

## Output

`markdown`, rendered by the official renderer built into `comline`:

| File | Contents |
|---|---|
| `index.md` | Package name and version, its `config.idp` `//!` header, a module table, a link to the changelog. |
| `<module>.md` | Per schema (`types::user` → `types/user.md`): its `//!` header, a table of its declarations, then each one with its `///` docs, annotations, fields and arguments (a field's own docs, else its parent's `/// @name:` line), enum variants, an error's ordinal and message, a validator's targets, parameters and asserts, and each protocol's functions and wire summary. |
| `changelog.md` | With a changelog: breaking changes, additions and other changes. |
| `nav.yml` | A `nav` list for mkdocs or zensical. |

Each declaration has an anchor, its name in lowercase; a function has
`<protocol>-<function>`. A type links to its declaration's anchor. A type from
a dependency links to `<base>/<module>/#<anchor>` when `[doc] links` gives the
dependency a base URL, and is plain text otherwise.

The wire summary has the rows [`comline inspect`](inspect.md) prints: the
format, framing and handshake with where each came from, then each guarantee,
held or given up, with its cause and acceptance.

`html`, rendered by the official HTML renderer, also built into `comline`,
writes a self-contained static site with the same content:

| File | Contents |
|---|---|
| `index.html` | As `index.md`. |
| `<module>.html` | As `<module>.md` (`types::user` → `types/user.html`), with the same anchors. |
| `changelog.html` | With a changelog: as `changelog.md`. |
| `style.css` | The theme: fixed, light and dark following the OS setting. |
| `search.js` | The search index (each declaration's name, kind, module and first line of docs), inlined as data, and the search box's script. |

Every page has a sidebar of modules and their declarations and a search box.
Doc text is rendered from Markdown to HTML; raw HTML in it is shown as text.
Nothing loads from the network and every link is relative, so `index.html`
opens straight from disk (the index is inlined because a browser blocks
`fetch` under `file://`) or from any static host. There is no `nav.yml`.

`json` writes `model.json`, the documentation model, in the shape of
[`doc-model/1.json`](../../schemas/doc-model/1.json).

## Built versions

With `--version`, the model comes from the version's frozen IR and the `//!`
headers stored with it. A built version keeps no source, so:

- its protocols have no wire summary;
- a type from a dependency has no link.

A version built before headers were stored has no headers.

## External renderers

`[doc] renderer = "<path>"` runs a renderer outside `comline`. It speaks the
[generator protocol](../generator-protocol.md#render), and runs like an
external generator: a `.wasm` under wasmtime with no filesystem, environment or
network, a native executable with an empty environment, the same time limit
(`[doc] timeout`, 60 seconds), output caps and path checks. `comline` asks it
to describe itself first and refuses it unless it lists the format, at the
model version this `comline` writes, in its `renderers`.

## Exit codes

`0` on success. `1` when the package doesn't compile, a version doesn't exist,
or the renderer refuses or fails. `2` when `--version` or `--changelog-from` is
given and the project was never built.
