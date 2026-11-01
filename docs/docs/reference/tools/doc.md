# comline doc

```
comline doc [--out <dir>] [--version <v>] [--changelog-from <v>] [--format <f>[,<f>...]]
```

`comline doc` writes a package's documentation for every version: each
release, each dev build, and the unreleased working state when it differs from
the last build. Like `comline check`, it writes nothing to `.comline/`. For a
walkthrough, see [Documenting your schemas](../../guide/documenting.md).

## Flags

| Flag | Default | Meaning |
|---|---|---|
| `--out <dir>` | `[doc] out`, else `docs/api` | Where to write, relative to the project. |
| `--version <v>` | every version | Document only this built version, into `<out>/<format>/<v>/`: a version string, a commit hash (4+ characters), or `HEAD`. |
| `--changelog-from <v>` | `[doc] changelog_from` | With `--version`: add what changed from built version `<v>` to the documented one. |
| `--format <f>` | `[doc] formats`, else `markdown` | `markdown`, `html`, `json`, or another renderer id `[doc] renderer` offers. Repeat it, or separate formats with commas. |

The `[doc]` keys are in [`comline.toml`](../congregation/comline-toml.md#doc),
including `versions`, which trims the list of versions.

## Versions and paths

Each format lands in `<out>/<format>/`, with one folder per version:

```text
docs/api/
├── html/
│   ├── index.html          # points at the latest version
│   ├── compare.html        # compare versions
│   ├── compare.js          # each version's structure and changes, inlined
│   ├── versions.js         # the version list, for the picker
│   ├── style.css
│   ├── .comline-doc.json   # the cache manifest
│   ├── 0.1.0/              # a release
│   ├── 0.2.0-dev.1/        # a dev build
│   ├── 0.2.0/              # the release it led to
│   └── unreleased/         # the working tree's changes since the last build
├── markdown/
│   ├── index.md            # the versions, grouped by release
│   ├── 0.1.0/ ...          # each with its own nav.yml
│   └── unreleased/
└── json/
    ├── index.json          # the versions, and where each model is
    ├── 0.1.0/model.json ...
    └── unreleased/model.json
```

- A dev build's folder is its full version (`0.2.0-dev.1`), and it belongs to
  the release it leads to (`0.2.0`).
- The working tree appears as `unreleased` only when its schemas or headers
  differ from the last build. With nothing built, it is the only version.
- Each version carries the changelog from the version before it in the list,
  computed by core with the same rules as `comline diff`. The first version
  has none.
- The latest version, which `index.html` points at, is the newest release,
  else the newest dev build, else the unreleased state.

**Caching.** A built version never changes, so its folder is kept between
runs. `<out>/<format>/.comline-doc.json` records each folder's key: the
version's commit, the commit of the version before it, the renderer's id and
version (and the `comline` version for a built-in renderer, or the renderer
file's hash for `[doc] renderer`), the model version and `[doc] links`. A
folder whose key still matches is left alone, so a run re-renders only the
unreleased state and new versions. A folder for a version no longer listed
(trimmed by `versions`, or the unreleased state once it's built) is removed.
`--version` writes its one folder and drops it from the manifest, so the next
full run re-renders it.

## Output

`markdown`, rendered by the official renderer built into `comline`, in each
version's folder:

| File | Contents |
|---|---|
| `index.md` | Package name and version, its `config.idp` `//!` header, a module table, a link to the changelog. |
| `<module>.md` | Per schema (`types::user` → `types/user.md`): its `//!` header, a table of its declarations, then each one with its `///` docs, annotations, fields and arguments (a field's own docs, else its parent's `/// @name:` line), enum variants, an error's ordinal and message, a validator's targets, parameters and asserts, and each protocol's functions and wire summary. |
| `changelog.md` | With a changelog: breaking changes, additions and other changes. |
| `nav.yml` | A `nav` list for mkdocs or zensical. |

`<out>/markdown/index.md` lists the versions, newest first, grouped by release.
There is no version picker: switching versions on a published site is left to
site tooling. With mkdocs, [mike](https://github.com/jimporter/mike) deploys
each version folder as a version of the site and adds a version selector.

Each declaration has an anchor, its name in lowercase; a function has
`<protocol>-<function>`. A type links to its declaration's anchor. A type from
a dependency links to `<base>/<module>/#<anchor>` when `[doc] links` gives the
dependency a base URL, and is plain text otherwise.

The wire summary has the rows [`comline inspect`](inspect.md) prints: the
format, framing and handshake with where each came from, then each guarantee,
held or given up, with its cause and acceptance.

`html`, rendered by the official HTML renderer, also built into `comline`,
writes a self-contained static site per version with the same content:

| File | Contents |
|---|---|
| `index.html` | As `index.md`. |
| `<module>.html` | As `<module>.md` (`types::user` → `types/user.html`), with the same anchors. |
| `changelog.html` | With a changelog: as `changelog.md`. |
| `style.css` | The theme: fixed, light and dark following the OS setting. |
| `search.js` | The search index (each declaration's name, kind, module and first line of docs), inlined as data, and the search box's script. |

Every page has a sidebar of modules and their declarations, a search box, and
a version picker in the header:

- The picker is a native drop-down, newest first, with dev builds grouped under
  the release they lead to, and a Go button. Choosing a version with the mouse
  goes at once. From the keyboard, the arrow keys move the choice, and Enter or
  Go navigates.
- It opens the same page and anchor in the chosen version when that version has
  them. Otherwise it opens that version's index, with a note saying what was
  missing.
- It is fed by `../versions.js`, so a version's pages don't change when
  versions are added, and it works under `file://`.

At `<out>/html/`, the site's root:

| File | Contents |
|---|---|
| `index.html` | Redirects to the latest version, and lists every version by release. |
| `compare.html` | Compare versions: tick two or more. |
| `compare.js` | Per version: its structure (each unit's kind, each member's type or signature) and its changes from the version before it, inlined as data, then the page's script. |
| `versions.js` | The version list, each version's pages and anchors, and the picker's script. |
| `style.css` | The same theme. |

On `compare.html`, two versions show what changed between them, grouped by
unit, each change labelled major, minor or patch, with the step it came from.
More versions show a grid with units and members as rows and the chosen
versions as columns. Each cell is the type or signature, or "absent", and a
unit's badge is the largest change across the range. The labels are never
computed in the browser. Core computes each version's changelog from the one
before it (breaking is major, a feature minor, anything else patch), and the
page only collects the steps after the older version up to the newer one. The
grid's cells are structural only.
Doc text is rendered from Markdown to HTML; raw HTML in it is shown as text.
Nothing loads from the network and every link is relative, so `index.html`
opens straight from disk (the index is inlined because a browser blocks
`fetch` under `file://`) or from any static host. There is no `nav.yml`.

`json` writes each version's `model.json`, the documentation model, in the
shape of [`doc-model/1.json`](../../schemas/doc-model/1.json), and
`<out>/json/index.json`: the package, the model version, the latest version,
and each version's `id`, `release`, `kind` and model path. Version 1 of the
model grows additively: new kinds and fields that may be absent keep the
version, so a reader should skip a `kind` it doesn't know and ignore unknown
fields.

## Built versions

A built version's model comes from its frozen IR and the `//!` headers stored
with it. A built version keeps no source, so:

- its protocols have no wire summary;
- a type from a dependency has no link.

A version built before headers were stored has no headers. Each page of such a
version opens with a note saying what it lacks, in both formats.

## External renderers

`[doc] renderer = "<path>"` runs a renderer outside `comline`. It speaks the
[generator protocol](../generator-protocol.md#render), and runs like an
external generator: a `.wasm` under wasmtime with no filesystem, environment or
network, a native executable with an empty environment, the same time limit
(`[doc] timeout`, 60 seconds), output caps and path checks. `comline` asks it
to describe itself first and refuses it unless it lists the format, at the
model version this `comline` writes, in its `renderers`. It renders each
version's folder with one `Render` each. The site's index is asked for only
when its `renderers` entry sets `sites`; one that doesn't gets the version
folders alone.

## Exit codes

`0` on success. `1` when the package doesn't compile, a version doesn't exist,
or the renderer refuses or fails. `2` when `--version` or `--changelog-from` is
given and the project was never built.
