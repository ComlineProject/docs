# Dependency packages in the editor

Status: **Proposal** · `ComlineProject/language-server` (+ small `core` and `cli` pieces) · Relates to core#6, core#50, language-server#24, language-server#25

How `use shared_types::foo::X` should work in the editor when `shared_types` is a
dependency declared in `config.idp`: hover, go-to-definition into the
dependency, completion, missing-import fixes, and a real error for a package that
doesn't exist. The language server never fetches anything itself.

## Where things stand (2026-10-04)

| Piece | State |
|---|---|
| `dependencies` block in `config.idp` (`Path` / `Git` / `Registry`) | ✅ parsed (core#50) |
| `Path` + `Git` resolution, hash check, CAS vendoring | ✅ `comline-core`'s opt-in `deps` feature (core#50); the CLI enables it, so `comline check` / `build` resolve dependencies |
| `Registry` dependencies | parsed, then rejected: there's no registry server yet (`package-registry` is on hold) |
| `comline add` | doesn't exist |
| Editor: `use` of a local schema | ✅ resolved across the whole package, open or not (language-server#22–#25) |
| Editor: `use` of a dependency | ❌ not resolved; names from it get the benefit of the doubt |
| `std::` | ❌ not resolved by `comline build` either (see below) |
| [Packages guide](../guide/packages/index.md) | outdated: still says dependencies aren't implemented |

## How the build resolves a dependency `use`

From core#50 (`core/src/package/deps.rs`):

- A dependency's **declared name becomes its namespace prefix**.
  `shared_types = { path = "../shared-types" }` makes the dependency's
  `src/foo.ids` the schema `shared_types::foo`, merged into the same pass as the
  package's own schemas, so `use shared_types::foo::X` resolves like any other
  `use`.
- **Where the sources come from:**
    - `Path`: relative to the consuming package's root.
    - `Git`: cloned by the `git` binary into
      `<package>/.comline/deps-cache/<blake3("{uri}#{commit}")>`, once per pin.
    - `Registry`: rejected.
- **Direct dependencies only.** The consumer sees the dependency's own `src/`
  (`glob_schema_sources`), not the dependency's dependencies.
- **A `use` that matches no schema is trusted, not reported.** When no schema has
  the namespace, the `use` lowers to a raw `FrozenUnit::Import` and the
  validator registers its last segment as a bare name. That covers
  `std::collections::HashMap` (std schemas aren't merged into builds), but also
  `use shard_types::foo::X` with a typo: `comline build` accepts it and never says
  the import is unresolved. A glob or whole-namespace `use` of an unknown
  namespace does fail, but only as "Unknown type" at each use site.

## Proposal

### 1. Find the package's dependencies, without fetching

On the workspace scan (language-server#25), and whenever a `config.idp` changes
(the VS Code client already watches `**/*.{ids,idp}`), the server would:

1. Parse each package's `config.idp` with core's grammar, and read `dependencies`
   with core's own `DependencyConfig::parse_dict`. That is plain parsing, not
   behind the `deps` feature, and wasm-safe.
2. Locate each dependency's sources:
    - **`Path`**: `<package>/<path>/src/**/*.ids`.
    - **`Git`**: the CLI's cache checkout, `.comline/deps-cache/<key>/src`, which
      exists once `comline check` or `build` has run. If it's missing, show a
      diagnostic on the entry in `config.idp` and on each `use` naming the
      dependency: "`shared_types` isn't fetched yet — run `comline check`". The
      editor never clones: that would mean network access, credentials and a `git`
      binary, from inside an editor process.
    - **`Registry`**: the same message the build gives ("registry dependencies
      aren't supported yet").
3. Index dependency files **read-only**, each under the namespace
   `[dependency name] + its namespace inside the dependency`.

Small changes this needs:

- **core:** make the cache-path computation public outside the `deps` gate, for
  example `deps::git_checkout_path(package_root, uri, commit)`. It's pure (blake3
  is already a default dependency), and it saves the editor from re-deriving the
  cache key, which would silently break if the key ever changes.
- **language-server:** `Project` takes each file's namespace from the caller
  instead of always deriving it from the file's URI. A dependency file's path says
  `foo`; the consumer sees `shared_types::foo`.
- **language-server:** index dependencies per consuming package and dependency
  name. Two packages may depend on the same directory under different names.

### 2. Resolution and diagnostics

With dependency files in each request's project view, everything built in
language-server#22–#25 works unchanged: go-to-definition, references, hover, the
import check, auto-import completion and the "Add `use ...`" quick fix.

On top of that:

- **Rename never edits a dependency's files.** Starting a rename on a symbol
  declared in a dependency is refused: it isn't this package's to change.
- **"Unresolved import" error.** A `use` whose first segment is none of these:
    - a local namespace,
    - a declared dependency,
    - `std`,
    - `self` / `parent` / `package`.

  Example: `use shard_types::foo::X` → "no schema or dependency named
  `shard_types` — declared dependencies: `shared_types`", with a quick fix to the
  closest name. This replaces the benefit of the doubt that globs and
  whole-namespace imports still get when their target exists nowhere (the known
  gap noted in language-server#25).
- **The build should agree.** Since `comline build` trusts unresolved
  single-symbol imports today, the editor's error would be stricter than the
  build's. Proposed: core reports an unresolved import in project mode too (`std`
  excepted until it's resolvable), so the editor and the build say the same
  thing. Until then, the editor reports it as a **warning**.

### 3. Completion for `use` paths

A `use` line gets no completion today (`use` counts as a declaration keyword, so
nothing is offered after it). With the project view above:

- `use ` → the package's top-level namespaces, its dependency names, `std`,
  `self`, `parent`, `package`.
- `use shared_types::` → the dependency's namespaces.
- `use shared_types::foo::` → its declarations, plus `{` and `*`.

### 4. `config.idp`

Key completion and hover for dependency entries already exist client-side
(`comline-vscode`'s `idpSchema.ts`). The server adds diagnostics on an entry:

- a `path` that doesn't exist or isn't a package (no `config.idp`);
- a `Git` pin that isn't fetched yet;
- a `Registry` source.

Checking the declared `hash` needs a full compile of the dependency. That stays
with `comline check`.

### 5. `comline add` (doesn't exist yet)

```
comline add shared_types --path ../shared-types
comline add net --git https://github.com/acme/net --commit 4f2c9e1 --version 1.2.0
```

It would:

1. write the entry into `config.idp` as a text edit, preserving the file's
   formatting;
2. resolve it once (fetch, compile, hash) with the existing `deps::resolve`;
3. write `hash = "blake3:…"`. That's the pin `resolve` already computes and only
   logs today ("Consider pinning").

A side effect that helps the editor: after `comline add`, a `Git` dependency's
cache checkout exists, so the editor can index it immediately. The registry form
waits for a registry.

## Phasing

1. **core**: public `git_checkout_path` (tiny).
2. **language-server**: read `config.idp`, index `Path` and fetched `Git`
   dependencies under their namespace, so resolution, completion, hover and
   definition work into dependencies, plus the "not fetched" diagnostics.
3. **language-server**: unresolved-import warnings and `use` path completion.
4. **cli**: `comline add`.
5. **core**: report unresolved imports in builds (then the editor makes them
   errors). Resolve `std` once its schemas ship with the toolchain.

## Open questions

1. **Unresolved single-symbol imports.** Should `comline build` reject them
   (proposed), or keep trusting them and the editor only warn?
2. **Whole-namespace imports.** The [`use` guide](../guide/idl/use.md) says
   `use pkg::types` makes items available *qualified only* (`pkg::types::User`).
   Core accepts bare `User` too: its whole-namespace expansion registers every
   name bare as well. The editor follows core since language-server#24. Which is
   intended? If the guide is right, core's expansion should register only the
   qualified names.
3. **Auto-import from dependencies.** Offer a dependency's types in auto-import
   completion (proposed: yes, after the package's own), or only after the
   dependency is already `use`d somewhere?
4. **Transitive dependencies.** The build exposes only direct dependencies.
   Intended (Cargo-like), or a side effect of globbing only the dependency's own
   `src/`?
5. **Docs.** The packages guide's "Dependencies (not implemented)" section has
   been outdated since core#50. Update it as part of this work, or separately?
