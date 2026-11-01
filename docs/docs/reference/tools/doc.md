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
- Each version carries the changelog from the version before it in the list
  (a step), computed by core with the same rules as `comline diff`. The first
  version has none.
- A release also carries everything since the previous release, compared
  directly between the two built versions, and its changelog page shows that
  (`0.1.0 to 0.2.0`), not the step. A release built from the same files as its
  last dev build still lists that dev build's changes. The first release, with
  none before it, shows its step.
- A dev build (or the unreleased state) after the first build following a
  release carries its changes since that release too: its page shows its step
  and links to them. These are measured from the real previous release even
  when `versions` trims it away.
- The latest version, which `index.html` points at, is the newest release,
  else the newest dev build, else the unreleased state.

**Caching.** A built version never changes, so its folder is kept between
runs. `<out>/<format>/.comline-doc.json` records each folder's key: the
version's commit, the commits its changelogs start from, the renderer's id and
version (for a built-in renderer, its crate version plus a content hash of
its sources and assets, `0.1.0+<hash>`, and the `comline` version; for
`[doc] renderer`, the renderer file's hash), the model version and `[doc] links`. A
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
| `index.md` | Package name and version, its `config.idp` `//!` header, a module table (Module, Summary), a Dependencies table (each dependency and the modules of it the package uses), a link to the changelog. |
| `<module>.md` | Per schema (`types::user` → `types/user.md`): its `//!` header, a table of its declarations (Item, Summary), then each one with its `///` docs, annotations, fields and arguments (a field's own docs, else its parent's `/// @name:` line), enum variants, an error's ordinal and message, a validator's targets, parameters and asserts, and each protocol's functions and wire summary. |
| `changelog.md` | With a changelog: breaking changes, additions and other changes. Each entry is a heading line (its severity, `MAJOR`, `MINOR` or `PATCH`, and a title such as `` `Orders.place`: signature changed `` linking to the declaration), then the change as a fenced `diff` block: the old IDL line with `-`, the new with `+`. An addition has only the `+` line, a removal only the `-` line, and a change with no IDL to show (a docstring, an error's ordinal, guarantees) a sentence instead. A release shows its changes since the previous release; a dev build its step, then a link to its changes since the last release, listed below it. |
| `deps/<package>/<module>.md` | Per module of a dependency without a published base URL: what the package reaches of it, as `<module>.md`. |
| `nav.yml` | A `nav` list for mkdocs or zensical: the package's modules, then a `Dependencies` section (a dependency's pages, or its published base URL). |

`<out>/markdown/index.md` lists the versions, newest first, grouped by release.
There is no version picker: switching versions on a published site is left to
site tooling. With mkdocs, [mike](https://github.com/jimporter/mike) deploys
each version folder as a version of the site and adds a version selector.

Each declaration has an anchor, its name in lowercase; a function has
`<protocol>-<function>`. A type links to its declaration's anchor. A type from
a dependency links to `<base>/<module>/#<anchor>` when `[doc] links` gives the
dependency a base URL; `std` defaults to the hosted std docs,
`https://comlineproject.github.io/docs/std/` (`std::http::HttpMethod` links to
`.../std/http/#httpmethod`). Otherwise it links to the dependency's own pages,
`deps/<package>/<module>.md`, and is plain text only when the package doesn't
reach that declaration.

**Dependencies.** Only the package's own modules are its modules. What it
reaches of each dependency, and of `std`, is listed apart: the declarations its
own use or re-export and what those use in turn, the same reach
[versioning](../versioning.md#dependencies) measures a dependency by. A dependency it reaches
nothing of isn't listed.

The wire summary has the rows [`comline inspect`](inspect.md) prints: the
format, framing and handshake with where each came from, then each guarantee,
held or given up, with its cause and acceptance.

`html`, rendered by the official HTML renderer, also built into `comline`,
writes a self-contained static site per version with the same content:

| File | Contents |
|---|---|
| `index.html` | As `index.md`. |
| `<module>.html` | As `<module>.md` (`types::user` → `types/user.html`), with the same anchors. |
| `changelog.html` | With a changelog: as `changelog.md`, with a severity badge, and the old and new lines marked `−` and `+` and syntax-highlighted. A dev build's changes since the last release are a collapsed section the line under its step opens. |
| `deps/<package>/<module>.html` | As `deps/<package>/<module>.md`. |
| `style.css` | The theme: fixed, light and dark following the OS setting unless the header's toggle picks one. |
| `search.js` | The search index (each declaration's name, kind, module and first line of docs), inlined as data, and the search box's script. |

Every page has a header with the package's name (the version is in the
picker beside it), a search box, a theme toggle and a version picker, and a
sidebar: the package's modules and their declarations, then a Dependencies
section, collapsed unless the page is a dependency's, with one group per
dependency. A group links to the dependency's published docs when it has a
base URL, else to its pages here:

```text
Overview
api
  struct Order ...
types
Dependencies            (collapsed)
  localdeps
    greeting            -> deps/localdeps/greeting.html
  std ↗                 -> https://comlineproject.github.io/docs/std/
    http                -> .../std/http/
Changelog
```

The header and sidebar work like this:

- The theme toggle cycles auto (the OS setting), light and dark. The choice is
  kept in the browser's `localStorage` where it's allowed, so it carries across
  pages and versions, and is applied before the page paints. Where storage is
  blocked it lasts for the page.

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
unit, each change shown as on `changelog.html` (badge, title, highlighted old
and new lines), with the step it came from. The root's pages have the theme
toggle too, and show the package's name alone.
More versions show a grid with units and members as rows and the chosen
versions as columns. Each cell is the type or signature, or "absent", and a
unit's badge is the largest change across the range. The labels are never
computed in the browser. Core computes each version's step from the one
before it (breaking is major, a feature minor, anything else patch), along
with each entry's old and new IDL lines (the documentation model's optional
`old` and `new` on a changelog entry), and the
page only collects the steps after the older version up to the newer one, never
a release's changes since the previous release. The
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
fields. `dependencies` lists what the package reaches of each dependency
(`package`, and `modules` holding only the units reached), and a changelog's
`span` says what it covers: `step` (the default, when absent), `release` or
`since_release`.

## Built versions

A built version's model comes from its frozen IR and the `//!` headers stored
with it. A built version keeps no source, so:

- its protocols have no wire summary.

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
