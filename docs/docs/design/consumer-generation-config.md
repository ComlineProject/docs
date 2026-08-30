# Consumer generation configuration

Status: **core feature shipped** · `ComlineProject/core` + `ComlineProject/cli` · Relates to core#6, core#8, cli#1

| Piece | State |
|---|---|
| Drop frozen `generation_path` + core-side codegen | ✅ merged (core#25) |
| Drop frozen `package_versions` from the congregation | ✅ merged (core#26) |
| `comline.toml` `[generate]`, `--out`/`--layout`/`--mode`, `generate` no longer freezes, `clean`/`new`/`watch` | ✅ merged (cli#10) |
| `COMLINE_GENERATE_*` env override layer | ✅ merged (cli#11) |
| `history` module (CAS-chain reader) | ✅ merged (cli#12) |
| Multi-version generation (`package_versions` = latest / list / all) | ✅ merged (cli#13) |
| Frozen config recorded in each CAS commit | ✅ merged (core#27) |
| Congregation changes drive the version bump | ✅ merged (core#28) |
| `comline clean` split into `clean` (generated code) + guarded `comline reset` (history) | ✅ merged (cli#15) |
| `lib` / `dylib` modes | not started — needs core#8 |
| `[generate.dependencies.*]` (generate for a registry dep) | not started — needs dependency resolution (core#6) |
| Per-historical-version `{{spec_version}}` | not started — cosmetic, low value |

## Problem

`comline generate` currently writes one file per schema namespace, named
`<namespace>.<ext>`, **flat into the project root**, next to `config.idp`
(`cli/src/commands/generate.rs`). There is no way for a consumer to say where
generated code should go, which of the declared targets to emit, or in what form.

The one place a path *could* be configured — `LanguageDetails.generation_path:
Option<String>` on `FrozenUnit::CodeGeneration` — is dead: hardcoded to `None` in
`freezing.rs`, and any key other than `package_versions` inside a language's
detail dict panics.

Output location is **a per-consumer concern**. Every downstream consumer of a
package wants a different layout, a different subset of targets, and possibly a
different generation mode. Baking it into `config.idp` — which is the package
author's declaration and is frozen, content-addressed, and published — would be
both wrong-layered and, because the frozen unit feeds the CAS hash, would make a
local path choice perturb the package's identity.

## Two files, two owners

| File | Owner | Format | Frozen into CAS | Purpose |
|---|---|---|---|---|
| `config.idp` (congregation) | package **author** | `.idp` | yes (interpreted → `Vec<FrozenUnit>`) | package identity + declarations: name, `specification_version`, `dependencies`, `publish_registries`, and the codegen **capability declaration** `code_generation.languages` = "this package *can* be generated as `rust#1.70`, `python#3.11`" |
| `comline.toml` | package **consumer** | TOML | **no** — never enters freezing or CAS | *what this checkout generates, in what mode, and where* |

The manifest stays in an `.idp` file. See
[Manifest filename](#manifest-filename-configidp-vs-comlineidp) for the
`config.idp` vs `comline.idp` question.

TOML for the consumer file: `toml_edit` is already a workspace dependency, it
reads as build tooling rather than schema, and core#6 already proposed the name
`comline.toml`.

## Resolution order

Built-in defaults → `comline.toml` `[generate]` → `COMLINE_*` env → CLI flags.
Each layer overrides the previous, field by field.

A later, optional machine-local layer sits between the file and env:
`.comline/config.toml` (git-ignored, next to the CAS store) plus `COMLINE_*`,
for machine-scoped things — the generator-plugin / runtime-schema-library search
directory from core#8 (`~/.comline/plugins/`, `./plugins/`), a shared cache dir,
a developer's personal output override.

## `comline.toml` — shape

```toml
# Consumer-owned. Commit it: the team and CI must agree on the layout.
# Nothing here is frozen or published.

[generate]
# Default output root for every target below. Relative to this file.
out = "generated"

# Layout of files under a target's root. Handlebars, strict mode.
# Vars: {{language}} {{namespace}} {{ext}} {{lang_version}} {{package_version}}
#       {{spec_version}}   (no bare {{version}} — three unrelated ones exist)
layout = "{{language}}/{{namespace}}.{{ext}}"

# Emit form for every target unless overridden:
#   "code"  — code_gen text only (paste into your own tree)   ← only one built today
#   "lib"   — lib_gen: a buildable crate skeleton (Cargo.toml + src/)
#   "dylib" — lib_gen + `cargo build --release`, for the language runtime to load
mode = "code"

# One block per target actually emitted. `language` must be one the
# congregation declared under `code_generation.languages`. Any language / mode
# string parses; `comline generate` errors if there is no generator for it yet.
[[generate.target]]
language     = "rust"
lang_version = "1.70.0"   # optional; picks the version-specific generator
# out / layout / mode / package_versions may be overridden here
# package_versions = ["0.3.0", "0.4.0"]   # subset of the congregation's; see scope cut below

[[generate.target]]
language     = "python"
lang_version = "3.11.0"
out          = "python/comline_gen"
mode         = "lib"

# Generating bindings for a registry dependency instead of the local schemas:
[generate.dependencies.stdlib]
out = "src/gen/stdlib"
targets = ["rust"]
```

Minimum viable slice for a first implementation: `[generate]` with `out`,
`layout`, `mode`, and `[[generate.target]]` with `language` / `version` /
per-target `out`. Dependency blocks and `versions` subsetting can follow.

## Changes in `core`

Status: **done** on branch `feature/drop-frozen-generation-path` (tests green).

1. ✅ Removed `generation_path` from `LanguageDetails`. A frozen codegen unit is
   now `{ name, versions }` — the capability declaration.
2. ✅ Removed the dead codegen block from `package/build/mod.rs`
   (`generate_code_for_targets`, `Args`, `resolve_path_query`,
   `generate_code_for_context`) and its now-unused imports (`codelib_gen`,
   `handlebars`, `serde_derive`). `core` no longer has a code path that writes
   generated files.
3. ✅ `freezing.rs::interpret_assignment_code_generation` unchanged in spirit —
   still rejects unknown detail keys; `package_versions` stays the only accepted
   one. It just no longer sets a path.
4. No fixture churn: the `.frozen/.../config` golden objects are stale artifacts
   of the removed `basic_storage` loader and are read by nothing (CAS uses
   `.comline/`).

Net: `core` stops having any opinion about *where* code goes. It only answers
"what can this package be generated as", from the frozen units.

> Caveat (see [CAS reproducibility gap](#related-cas-reproducibility-gap)): the
> frozen congregation is **not** currently written into a CAS commit at all — only
> the frozen schemas are. So "the codegen capability declaration lives in the
> frozen config" presumes the frozen config is (re-)added to what each version's
> tree stores. That is a separate fix, but this proposal depends on it if the
> declaration is to travel with a published version.

## Changes in `cli`

Landed in cli#10 (branch `feature/comline-toml-generate`). New `src/gen_config.rs`.

1. ✅ `ComlineToml::load` (`serde` + `toml`) parses `[generate]` /
   `[[generate.target]]`; absent file ⇒ all-defaults. Accepts **any** `mode` /
   `language` string — validation happens at generate time.
2. ✅ Resolution `gen_config::resolve`: defaults → `[generate]` →
   `[[generate.target]]` → CLI flags, per field. (Env layer not yet wired — see
   [`COMLINE_*` env layer](#comline_generate_-env-layer).)
3. ✅ `comline generate` **no longer freezes** — `compile_package()` only, no
   version bump, no `.comline/` write.
4. ✅ `--out` / `--layout` / `--mode`; with more than one target they require
   `--target` and bind to that one. `layout` rendered by
   `comline_core::utils::templating::recurse_render` via `ResolvedTarget::dest_for`;
   the target loop is CLI-side.
5. ✅ Per target: unknown `mode` or no `find_generator` → a specific error, never
   a silent skip.
6. ✅ `comline clean` resolves output the same way; removes the output root when
   it is a dedicated directory, else the individual files.
7. ✅ `comline generate --watch` and `--watch` in general also watch
   `comline.toml`.
8. ✅ `comline new` scaffolds an all-commented `comline.toml` (committed).
9. ✅ `tests/cli_tests.rs` split into `tests/cli/` (one module per area).

### `COMLINE_GENERATE_*` env layer

Landed in cli#11. `COMLINE_GENERATE_OUT` / `_LAYOUT` / `_MODE` sit between the
file and the flags (`defaults → comline.toml → env → flags`). Unlike the flags
they apply to **every** target regardless of `--target` — a deliberate CI global,
where one output root for a multi-target project is the common case and a bare
`--out` would be rejected as ambiguous. Empty vars are ignored.

## Migration

Pre-`comline.toml` projects: `generate` with no config file changes from
"flat `<namespace>.<ext>` in the project root" to the default
`out = "generated"` + `layout = "{{language}}/{{namespace}}.{{ext}}"`. This is a
visible behavior change for `comline generate`; acceptable while Comline is
pre-1.0, with a changelog note. Projects that want the old flat layout set
`out = "."` and `layout = "{{namespace}}.{{ext}}"`.

## Related: CAS reproducibility gap

Not part of this proposal, but it bounds what "the frozen config" can mean.
Inspecting `core/src/package/build/cas/`:

A CAS commit is `{ tree, parents, author, timestamp, message, version }`, and the
`tree` is built **only from `latest_project.schema_contexts`** — the frozen
schemas. What is *not* in a commit:

- **The congregation.** `latest_project.config_frozen` (the `Namespace`,
  `SpecificationVersion`, `Dependency`, `CodeGeneration`, `PublishRegistry`
  units) is compiled but never written into the tree. `grep config_frozen` across
  the CAS build code returns nothing. The pre-CAS `basic_storage` layout *did*
  store a per-version `config` blob (still visible in
  `tests/fixtures/packages/test/.frozen/.../<ver>/config`); the CAS rewrite
  dropped it.
- **Dependencies.** No resolution happens — `compile_package` just globs local
  `src/**/*.ids`. A `dependencies = { … uri, hash = "blake3:…" }` block is parsed
  into `Dependency { author, project, version }` (the frozen struct doesn't even
  retain `uri` / `hash`) and then goes nowhere: not fetched, not pinned, not
  stored. Issue core#6's "schema dependency resolution" is still unchecked.
- **`specification_version`**, and schema identity — subtrees are named
  `schema_0`, `schema_1` by iteration index ("*Use index as name since path field
  doesn't exist*"), so the index-keyed diff misaligns if a file is added, removed
  or reordered mid-list.

So the CAS store covers only **half** of a state-freezing story: version history
+ diff-driven auto-versioning, i.e. the "track past/present state" half. It does
**not** yet cover the "make a rebuild reproducible" half — freezing configuration
and pinning imported / dependency schemas. For that, a version's tree needs (at
least) the frozen config committed back alongside the schema entries, and — once
dependency resolution exists — the resolved dependency set (identity + integrity
hash, ideally content) captured in the commit.

### What config changes mean for the version — decided 2026-08-30

**Phase A** (core#27, merged) records the frozen config in each commit's root
tree as a `config` blob. **Phase B** (core#28, merged) wires the config diff
into the bump per the table below — `analyze_config_changes` in
`package::config::ir::diff::analyze`. Live today: `specification_version` change →
major. The dependency arms are implemented but dormant until a `dependencies`
block is interpreted into `FrozenUnit::Dependency` (part of core#6).

Once the frozen config is in the commit tree, the diff engine's "tree changed →
bump" logic sees config changes too. Not every config unit should move the
package version: the version is a statement about the **schema API**, so only the
units that affect that API feed the bump. The rest are *recorded* (for
reproducibility) but *not diffed*.

| Frozen config unit | Change | Version bump |
|---|---|---|
| `Dependency` | **removed**, or **version changed** | **major** — conservative: without dependency resolution we cannot tell a compatible dep bump from a breaking one, and a dep's schema shapes are part of this package's effective surface. Refine later (dep-major → major, dep-minor → minor) once core#6 can diff dep schemas. |
| `Dependency` | **added** | **minor** — additive; the schema content that uses the new dep already carries its own minor/major. |
| `Dependency` | `uri` / `hash` only, same version | **patch** — provenance, not API. |
| `SpecificationVersion` | changed | **major** — the meaning of the schema syntax itself may have changed. Rare. |
| `CodeGeneration` | any (add / remove / `lang_version` change) | **none** — pure tooling-capability metadata, orthogonal to the schema API. Recorded, never diffed. |
| `PublishRegistry` | any | **none** — publish metadata. Recorded, never diffed. |
| `Namespace` | changed | **not a version bump** — renaming the package is a new package; should be rejected or warned, not bumped. |

Rationale for excluding `CodeGeneration`: after the `generation_path` /
`package_versions` removals it is a bare `language#lang_version` capability list.
Whether the author lists `python` says nothing about the wire format or types, so
`generated/rust/0.5.0/` vs `0.6.0/` differing only because `python#3.11.0` was
added to a list would be misleading. Keep the version number about the schema.

The add / remove / re-pin split for `Dependency` (rather than one flat "any
change → major") is the agreed rule — it avoids a surprising major bump for
adding an unused dependency, and it degrades safely: removal and version change,
the cases we cannot prove non-breaking, are the ones that go major.

## Unresolved before / during implementation

### v1 scope cuts (implementation reality)

- **Only `mode = "code"` + the built-in `rust` generator exist.** `lib` / `dylib`
  live in the unmigrated `generation` repo and depend on core#8 (plugin ABI);
  `python` / `lua` / `luau` / `c` generators don't exist in `core`. Parse `mode`
  and `language` generally, but the CLI should error clearly on anything but
  `code` + `rust` until those land.
- **Multi-version generation is unbuilt.** `comline generate` only ever produces
  the *latest* frozen schemas; nothing loads a historical version from CAS to
  generate it. So `package_versions = [all]` has no operational meaning yet, and
  `{{package_version}}` in a layout is always the current build. The v1 default
  layout omits it (`{{language}}/{{namespace}}.{{ext}}`); reintroduce once a
  `--version <ver>` path that reads historical schemas from CAS exists.
- **"Downstream app generates from a registry dependency" does not work.** That
  needs dependency resolution (core#6), which doesn't exist — `generate` requires
  a local `config.idp` + `src/*.ids`. The `[generate.dependencies.*]` block in
  the shape above is forward-looking only.

### Resolved (2026-08-30)

- **Version template vars** — no bare `{{version}}`; expose `{{lang_version}}`,
  `{{package_version}}`, `{{spec_version}}` explicitly (`FrozenUnit::PackageVersion`
  is defined but never populated; the manifest has no version field — package
  semver comes from the CAS ref).
- **`comline generate` does not freeze** — uses `compile_package()` for the
  latest; freezes only when a historical version is explicitly requested.
- **CLI override flags** (`--out` / `--mode` / `--layout`) require `--target
  <lang>` when >1 target is configured and override only that target; error
  without it. `--target` alone just filters which targets run.
- **Unimplemented `mode` / `language`** — the `comline.toml` parser accepts any
  string; `comline generate` errors per target with a specific message, never
  silently skips.

### Still needs a decision — `lib_gen` crate identity (deferred, gated on `mode = "lib"`)

The one-line version ("read it from the CAS ref") is right but hides several
sub-decisions. Deferred until `mode = "lib"` / `"dylib"` is built, recorded here
so it is not rediscovered.

**First, the framing question: is the generated crate the *package's* identity or
a *consumer build artifact*?**

- *Mirror* — the crate **is** the comline package, transliterated. `name` =
  congregation name, `version` = CAS package version; a schema change bumps the
  crate version the same way it bumps the package. Right when the consumer
  **publishes** the generated crate ("the official Rust binding for `acme-api`")
  or reasons about compat (`acme-api-schema >=0.4`).
- *Artifact* — like `prost-build` / `bindgen` output in `OUT_DIR`: `path`-depended
  on locally, never published, so its name/version barely matter. This is the
  natural reading of `mode = "dylib"` (the runtime loads it; nothing depends on it
  by name).

Both are legitimate and the consumer picks — which is why it is `comline.toml`
territory. But there is a strong default: **mirror**.

**Name**

- Default: the congregation name (`FrozenUnit::Namespace`, from the manifest),
  run through a per-language normaliser — a valid Comline identifier is not
  necessarily a valid crate / PyPI / Lua-module name.
- Override: optional `package_name` (or `crate_name`) on `[[generate.target]]`,
  for consumers who publish or must fit a naming scheme. Possibly a mode/lang
  suffix convention (`-schema`, `-types`) left to the override.

**Version**

- Source of truth: the CAS ref (`refs/heads/main` → `Commit.version`). **The
  manifest never carries a version** — a hand-written version would drift from
  and fight the diff engine's auto-versioning. Settled non-option.
- No CAS history yet (`generate` before any `build`, now that `generate` no
  longer freezes): either require one `comline build` first for `mode =
  lib|dylib`, or fall back to `0.0.0` with a warning.
- Dirty working tree (schemas changed since the last commit): `Commit.version` is
  stale. Options — (a) refuse / warn "generating a stale version"; (b) stamp it
  as-is; (c) run the diff *without* committing, stamp the prospective
  `X.Y.Z-dev` plus a short `Commit.tree` hash. (c) is nicest and needs a
  diff-without-freeze path (compatible with the `compile_package()` decision).
- Override: a `version` field in `comline.toml`, allowed but discouraged (defeats
  auto-versioning).

**`dylib` load-time identity is a different thing from `Cargo.toml` metadata**

What the runtime must verify when it loads a compiled schema library is
`(package_name, package_version, spec_version, frozen-schema hash)` — and that
belongs **embedded in the generated code** (a `pub const`, matching the existing
"this file is hashed, the runtime will complain" generation note), not just in
`Cargo.toml`. `Commit.tree` already gives a per-version content hash to use.
`[package] version` there is near-cosmetic — it only has to be valid semver.

**A fourth version axis appears here**

Beyond lang/toolchain, package semver and `spec_version`: the **generator /
plugin version and its ABI contract** (core#8). `lib_gen`'s generated
`Cargo.toml` needs `comline-runtime = "<generator-pinned>"` and (for
`rust_abi_stable`) `abi_stable = "<generator-pinned>"`, and the `dylib` needs an
embedded ABI tag the loader gates on. Those come from the generator, not the
schema.

### Deferred / minor

- Formatter / post-process hook (`rustfmt`, `black`) — in `[generate]` or out.
- Stale-output pruning: `generate` after a schema file is deleted leaves orphan
  files; only `clean` removes anything today.
- Whether `comline new` adds `out` to `.gitignore` (teams differ on committing
  generated code).
- Exact `COMLINE_*` variable names.
- A `[registries]` section for dependency-fetch sources (cargo
  `.cargo/config.toml` model) — future, with core#6.
- Generator completeness: cross-schema `import`s aren't emitted as `use` /
  `import` in generated code, so multi-file output references symbols it never
  brings into scope — and the `layout` sub-directory structure makes the module
  paths load-bearing.

## Rejected

- **Path inside `FrozenUnit` / the congregation** — pollutes the CAS hash with a
  local choice; wrong owner. This is the whole reason for the split.
- **Prisma-style `generator {}` blocks in `.ids` schemas** — same problem, inside
  the shared, frozen artifact.
- **A non-frozen section inside `config.idp`** — mixes frozen and non-frozen
  content in one file (easy to freeze by accident) and does nothing for
  downstream apps that have no `config.idp`.

## Open questions

### Manifest filename: `config.idp` vs `comline.idp`

`config.idp` is hardcoded (`CONGREGATION_EXTENSION = "idp"`, stem `config` in
`build/mod.rs` and `package/config/mod.rs`). The `.idp` extension already means
"Interface Definition **Package**", so the `config` stem is a little vague but
harmless.

- **Keep `config.idp`.** It is what `comline new` scaffolds, what every fixture,
  test, doc and the CLI guide use (~14 files across core + cli plus every fixture
  dir). The extension already disambiguates it. Changing it is a mechanical but
  wide breaking rename for a marginal clarity gain.
- **Rename to `comline.idp`.** Gives a memorable pair — the two Comline files in
  a project are `comline.idp` (manifest, frozen) and `comline.toml` (generate,
  local). Downside: breaking rename; two `comline.*` files could read as "which
  is which".

Recommendation: **keep `config.idp`** unless the rename is done deliberately as
its own change. If renamed, `comline.idp` is the target.

### Other

- **Committed, not git-ignored** (resolved). Consumers rarely change it, and
  Comline has **no separate lock file** — there is no `state.lock` /
  `comline.lock` in `core` or `cli`; dependency integrity is pinned inline in the
  manifest (`dependencies = { stdlib = { version, uri, hash = "blake3:…" } }`).
  Committing `comline.toml` keeps the team and CI in agreement, consistent with
  how the manifest is already handled. It is plain committed source — unrelated
  to `.comline/` below.

  > `.comline/` (the CAS store) is **not** disposable build output. It is the
  > authoritative, append-only history of the package's versions and is what a
  > publish pushes to a registry so history is tracked without gaps. It is
  > git-ignored in the `comline new` scaffold mainly to keep test- and
  > example-generated stores out of version control; a package meant for
  > publication needs its `.comline/` preserved. Orthogonal to this proposal, but
  > worth not mischaracterizing.
- **Schema input path stays manifest-side** (resolved). `comline.toml` does *not*
  own the `schemas_source_path` / `schema_paths` stub (`freezing.rs`, hardcoded to
  `<pkg>/src/**/*.ids`). Where a package's schemas live defines what the package
  *is* — package-author territory, belongs in the `.idp` manifest if made
  configurable at all. No reason found to make it a consumer setting.
- **Monorepo form** (still open — needs investigation). A repo-root `comline.toml`
  with `[[package]]` entries covering several schema packages / dependencies at
  once: how it composes with per-package files, path resolution, target merging.
