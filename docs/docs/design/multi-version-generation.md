# Multi-version generation

Status: **implemented** (core#26 merged; cli#12 merged; cli#13 open, CI green) · Follows [Consumer generation configuration](consumer-generation-config.md)

Shipped: `[generate].package_versions` / `[[generate.target]].package_versions` =
`"latest"` (default) | `"all"` | version-or-hash list; `latest` uses the live
context, the rest walk the CAS chain (`history` module) and require a prior
build; `{{package_version}}` is a real layout var and mandatory when >1 version
is selected. Not shipped: `--version` one-off flag, `COMLINE_GENERATE_VERSIONS`,
per-historical-version `{{spec_version}}` (frozen config not in CAS).

Decisions (2026-08-30): (1) **drop `package_versions` from the congregation** —
selection lives only in `comline.toml`; (2) `{{package_version}}` for the live
working tree = **the last commit's version** (empty if never built); (3)
**`"all"` is supported** = every committed version, cost documented.

## Use case

A package is at `0.5.0` today. A consumer's app was written against `0.3.0` and
also talks to a service still on `0.4.0`. They want bindings for several
historical versions side by side:

```
generated/rust/0.3.0/…
generated/rust/0.4.0/…
generated/rust/0.5.0/…
```

That is what `package_versions = [all]` in the congregation and `{{version}}` in
the dead `default_path` template were always gesturing at. Neither is wired to
anything.

## What already exists

Everything the feature needs is in place; it has just never been connected.

- **CAS history walk.** `cli/src/commands/diff.rs` already does the whole job for
  two versions: `refs::read_ref(main_ref())` → `walk_history(store, head)` (follow
  first parent, newest-first) → `resolve(&history, spec)` (`HEAD` | version string
  | full/short commit hash) → `load_schemas(store, commit)` →
  `Vec<Vec<FrozenUnit>>` via `cas::blob::load_schema_from_tree`.
- **Namespace from frozen units.** `comline_core::schema::ir::frozen::unit::schema_namespace_as_path(&[FrozenUnit]) -> Option<String>`
  (`::` → `/`). `build_tree_from_schema` stores *every* unit including
  `FrozenUnit::Namespace`, so a CAS-loaded historical schema carries its own
  namespace — no live `SchemaContext` needed.
- **The generator loop.** `gen_config::ResolvedTarget` + `find_generator` +
  `dest_for` already turn `(namespace, ext, layout)` into a path and write it.
- **`package_versions`.** Parsed into `LanguageDetails.versions: Vec<String>`
  and frozen as `FrozenUnit::CodeGeneration { name, versions }`. `[all]` becomes
  `versions = ["all"]`. Nothing reads it.

### Not blocked

Earlier notes listed this as "blocked — no CAS-historical read path." That was
wrong: `diff.rs` is the read path. The only genuinely missing work is wiring, a
version-selection design, and one behaviour decision about the live/dirty tree.

## Design

### 1. Where the version list comes from

Consistent with the output-config split: **the consumer chooses**, in
`comline.toml`:

```toml
[[generate.target]]
language = "rust"
package_versions = "all"            # or ["0.3.0", "0.4.0"] or "latest" (default)
```

- unset / `"latest"` → the working tree only (today's behaviour)
- `["0.3.0", "0.4.0"]` → exactly those committed versions
- `"all"` → every committed version in the chain
- (later, maybe) a semver range `">=0.3, <0.6"`, or `"latest-3"`

`[generate]` may set a default `package_versions` for every target.

### 2. The congregation's `package_versions` — dropped (decided)

Same mistake as `generation_path`: *which historical versions to realise* is a
consumer decision, and freezing it into `FrozenUnit::CodeGeneration` bakes a
consumer choice into the package's content hash.

- Remove `versions` from `LanguageDetails`; `FrozenUnit::CodeGeneration` becomes
  `{ name }` (just the declared `language#lang_version`).
- `freezing.rs::interpret_assignment_code_generation` stops accepting the
  `package_versions` detail key — a language's detail dict now takes **no** keys
  (`rust#1.70.0 = {}`); revisit whether the `= { … }` syntax is still worth
  keeping.
- `comline new` scaffold: `rust#1.70.0 = {}`. Update the `config.idp` fixtures in
  both repos and the `.frozen`/CAS goldens if any encode it.
- Every `package_versions=[all]` in docs/examples goes away.

A second small breaking change to the congregation, same spirit as core#25 — its
own `comline-core` PR, landed before the CLI work so the CLI builds against the
new `FrozenUnit` shape.

### 3. Live vs historical

- **`"latest"`** keeps using `compile_package()` — the working tree, possibly
  ahead of the last commit, no CAS needed.
- **Any pinned version or `"all"`** requires `.comline/` (a `build` must have
  happened) and goes through the `diff.rs` history machinery.

`{{package_version}}` for the **live** case (decided): the **last commit's
version** (`walk_history` first entry) if `.comline/` exists, otherwise the empty
string. It can be stale if the working tree has uncommitted schema edits; that is
acceptable for v1 and revisited with the reproducibility work.

### 4. `{{package_version}}` in `layout`

- It becomes a real template variable (drop the "not available yet" guard in
  `ResolvedTarget::dest_for`).
- If more than one version is selected and `layout` does **not** contain
  `{{package_version}}`, that is an error — otherwise every version writes to the
  same paths and clobbers.

### 5. Which generator runs on old schemas

Today's generator (`find_generator(language, lang_version)` from the *current*
`comline.toml` / declared language), not a version-matched one. You want current,
idiomatic output for an old schema shape. No per-historical-version generator
selection.

### 6. CLI surface

Config-driven is enough; a `--version <spec>` flag is a nice one-off
(`comline generate --target rust --version 0.3.0`), overriding
`package_versions` for that run, subject to the same "needs `--target` when
several targets" rule as the other overrides. Env: `COMLINE_GENERATE_VERSIONS`
for parity, low priority.

### 7. `comline clean`

`clean` resolves the same config; if `dest_for` learns `{{package_version}}` and
`clean` passes the selected versions through, it prunes the multi-version tree
correctly. In practice removing the `out` root (the common case) already covers
it.

### 8. Factoring

`walk_history` / `resolve` / `load_schemas` are private to `cli/src/commands/diff.rs`.
Multi-version generate needs the same three. Move them to a shared `cli` module
(`src/history.rs`) that both `diff` and `generate` use. All the `comline-core`
API they touch is already public (`cas::objects`, `cas::storage::Hash`,
`cas::{refs, ObjectStore}`, `frozen::cas::blob::load_schema_from_tree`), so this
stays CLI-side — no `comline-core` change required, though a
`comline_core::package::history` module would be a reasonable home if other tools
want it.

## Open questions (remaining)

- Semver-range selection (`">=0.3, <0.6"`, `"latest-3"`) — later, not v1.
- With `package_versions` gone, is `rust#1.70.0 = {}` (empty dict) still the right
  syntax, or should a declared language just be a bare `rust#1.70.0` /
  `rust#1.70.0 = true`? Grammar question for the congregation PR.
- Does `diff.rs`'s position-paired schema model matter here? No — each version
  generates independently; no pairing.

## Phasing

1. **`comline-core` PR** — drop `versions` from `LanguageDetails` /
   `FrozenUnit::CodeGeneration`; stop parsing `package_versions`; update scaffold
   references, fixtures, goldens. (Breaking; lands first.)
2. **`cli` PR — `history.rs`** — factor `walk_history` / `resolve` /
   `load_schemas` out of `commands/diff.rs` into `src/history.rs`; `diff` uses it.
   Pure refactor, no behaviour change.
3. **`cli` PR — selection** — `[[generate.target]].package_versions` (+
   `[generate]` default) parsing `"latest"` (default) / `["x","y"]` / `"all"` in
   `gen_config`; resolve against `history.rs`.
4. **`cli` PR — generate the versions** — for `"latest"`, unchanged
   (`compile_package`, `{{package_version}}` = last commit's version). For the
   rest: walk history, `load_schemas` per resolved version, run the generator
   loop with `{{package_version}} = commit.version` and the namespace from
   `schema_namespace_as_path`. Require `{{package_version}}` in `layout` when the
   selection resolves to more than one version; drop the guard in `dest_for`.
   Pinned/`all` selections error without `.comline/`.
5. **`cli` PR — edges** — `--version <spec>` one-off override; `clean` threads the
   selected versions through `dest_for`; docs.
