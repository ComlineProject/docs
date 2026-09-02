# Generation — codegen, libgen, and the `generation` repo

Status: **G1 + G2a + G2b + G3 done** — codegen is out of `core` (the CLI is the
composition root); `mode = "lib"` emits a buildable rust crate; TypeScript has a
`code` generator; each generator now lives in its own `comline-<lang>` repo.
`comline-codegen-rust` also generates the **RPC shape** for a `protocol` —
params structs, error enums (from `throws` ordinals), a provider trait, a
`Dispatch` impl, and a `Client` stub against `comline-runtime` ([surface 4.2](core-target-contract.md#42-the-generated-protocol)).
G2c (FFI / `dylib`) not started · Affects `ComlineProject/core`,
`ComlineProject/generation`, `ComlineProject/cli`, `ComlineProject/comline-<lang>`

Companion to [Runtime & generation repository structure](runtime-repo-structure.md),
which decided **one repo per target language** (Option E). This page fixes what
the pieces *are* and tracks the `generation` cleanup. The endpoint has moved:
G0–G2 got the generators *out of `core`* and into `generation` as pure,
CLI-driven functions — still the necessary first step — and G3 takes each
language's generator the rest of the way, into its `comline-<lang>` repo, with
`generation` left as `comline-codegen`, the shared support crate.

## Vocabulary

Three distinct things. The names have been used loosely; these are the fixed
meanings.

| Term | Input → output | `comline.toml` `mode` | Runs where |
|---|---|---|---|
| **code generation** (*codegen*) | frozen IR → **source text** in a target language — `struct`/`enum` types, a trait/interface per protocol | `"code"` | the consumer's build, via `comline generate` |
| **library generation** (*libgen*) | IR + generated source → **a loadable library**: the package manifest (`Cargo.toml` / `pyproject.toml` / `.rockspec`), an FFI wrapper, build glue (`cbindgen.toml`, …), and — for `dylib` — the compiled artifact | `"lib"` / `"dylib"` | same |
| **runtime** | *nothing* — it is hand-written, not generated. Transport, call framing, routing. | — | run time, linked by the generated library |

- **codegen** gives you *types and stubs* in language X.
- **libgen** wraps those into something language X can *load and call* — the FFI
  boundary plus a package its ecosystem understands. It is codegen's packaging
  layer, not a separate pipeline.
- **runtime** is the fixed library the loaded thing talks to for actual
  dispatch. It is never generated; `generation` only produces the *schema types*
  the runtime needs.

In the repo these are already the module names — `generation/lib-gen/_core/src/`
has `code_gen/` and `lib_gen/` side by side, and every per-language crate mirrors
that pair.

### Doc alignment

Done: the guide page "Runtime libraries" is renamed
[Library generation](../guide/codegen/library-generation.md) (it generates the
loadable library the runtime consumes; "runtime" now means only the hand-written
layer), and [Codegen by language](codegen-by-language.md) states in its first
line that it shows codegen *source* output, not libgen.

## Where codegen lives

**Done: the generators are out of `core`.** `core` ships no generator; it is the
compiler + IR. They landed in `generation` as an intermediate.

**Endpoint ([repo decision](runtime-repo-structure.md)): each language's
generator lives in its `comline-<lang>` repo**, next to that language's runtime.
`generation` becomes **`comline-codegen`** — the shared, language-neutral support
crate (contract + `FrozenUnit` helpers + `Registry` type, one dep on
`comline-core`) that every `comline-<lang>` depends on.

- **No `comline-core-ir` carve-out.** `comline-core` is the whole unit.
  `comline-codegen` and every `comline-<lang>` depend on it **by git rev** — no
  crates.io publishing at this stage (see the
  [repo decision](runtime-repo-structure.md)); the cost is coordinated rev bumps.
- **The CLI is the composition root.** It depends on `comline-core` (source → IR)
  and, behind cargo features, the `comline-<lang>` generator crates (IR → code /
  lib), and wires them together. `core` knows nothing about codegen.

```
core ──► comline-codegen ──► comline-<lang> ──► cli
(idl→ir)  (contract + helpers)  (ir → code / lib;   (composition root:
                                 lives with the      compile, then generate
                                 language runtime)   with the enabled targets)
```

`comline-codegen` depends on `core`. Each `comline-<lang>` depends on both. The
runtime for a language sits in the same `comline-<lang>` repo but is a separate
crate: hand-written, linked at the consumer's build, and the schema types it
needs are that repo's own codegen output.

## `generation` de-rot plan

G0–G2 (out of `core`, into `generation` as CLI-driven functions) are done or
scoped; **G3** (out of `generation`, into `comline-<lang>` repos) is the new
endpoint under the [repo decision](runtime-repo-structure.md).

### G0 — make the build system honest ✅

Landed (`generation` `chore/derot-g0`). Scope was the manifest / workspace / CI
layer only — the crate bodies still don't compile (that is G1).

1. **Build junk** — `__TEMP__/`, `target/`, `Cargo.lock` were already
   `.gitignore`d, so the cmake / ninja / `a.out` cruft under `lib-gen/c/tests/`
   was never committed. Added `cmake-build-*/`; removed the stale on-disk
   `Cargo.lock` / `lib-gen/_core/Cargo.lock` that were forcing a `regex-syntax`
   resolution conflict.
2. **One dependency convention** — `comline-core = "0.1"` in every crate that
   needs it (matching `cli`); a single workspace-root `[patch.crates-io]` →
   `../core/core`, kept **active** with a comment that it stays until `generation`
   pins a published `comline-core` (post-G1). Deleted the `htpps://` typo, the
   version-less git dep, and the stray per-crate commented `[patch]` blocks.
3. **Removed the vestigial `code-gen/*` workspace glob** — the split is the
   `code_gen` / `lib_gen` *modules* inside each crate, not top-level directories.
4. **Explicit workspace members** — `_core`, `lua`, `luau` (the wired crates);
   `c` / `python` / `typescript` commented with a "not started" note (they still
   `use comline::…`, the pre-rename crate path). `cargo metadata` now resolves.
5. **CI** — `actions/checkout@v4`, dropped the beta/nightly matrix; `cargo build`
   / `cargo test` run with `continue-on-error` and a `TODO(de-rot G1)` to remove
   it once the bodies are ported.

**State after G0:** the workspace resolves and the manifests are clean;
`cargo build` fails with ~18 pre-audit-IR errors in `_core` (missing `span`
fields, 1-vs-2-field `EnumVariant`, `basic_storage` imports, a dropped
`package_from_path_without_context`). Those are G1.

### G1a — working `rust` codegen in `generation` ✅

Landed (`generation` `chore/derot-g1`, PR #2, stacked on #1).

6. Ported `core/core/src/codelib_gen/rust.rs` **verbatim** into
   `code_gen/rust/generator.rs` (renamed from the pre-audit-IR `_1_7_0.rs`
   stub). `generation` and `core` now emit byte-identical Rust, so the G1b
   switch is output-neutral. `find_generator` keeps its version-keyed shape with
   one `"1.70.0"` entry.
7. **Gated for G2** (they call `basic_storage` / `package_from_path_without_context`,
   removed from `core`) — bodies kept in-tree: `code_gen::rust_c_ffi`,
   `code_gen::rust_abi_stable`, all of `lib_gen`. Deleted
   `generate_frozen_schemas_into_path` — the CLI owns that orchestration.
8. `_core` is the sole workspace member (`lua` / `luau` bodies have the same IR
   drift → G2); dropped `abi_stable` / `cbindgen` / `toml_edit` / `glob` /
   `heck`; ported `core`'s three codegen unit tests; CI back to blocking
   (`cargo build` / `cargo test` green).

### G1b — flip the switch ✅

Landed — `core` `b2739a4` (#41), `cli` `eb69a60` (#16).

9. **core#41** — deleted `core/core/src/codelib_gen/` + `pub mod codelib_gen;`
   and `core/core/tests/codelib_gen/` (ported to `generation` in G1a). `core` is
   the compiler + IR; it ships no generator.
10. **cli#16** — added `comline-codelib-gen` (a `generation` git rev) and moved
    `comline-core` from crates.io `0.1.0` to the **same** `core` git rev the
    generator crate pins, so the tree holds one `comline-core`. Repointed
    `find_generator` to `comline_codelib_gen::code_gen::find_generator` in
    `generate.rs` / `clean.rs`.
11. Behaviour delta — `generation`'s `find_generator` is version-exact (only
    `"1.70.0"` registered); `core`'s ignored the version. All fixtures and
    `comline new` use `rust#1.70.0`, so no test churn.

### G2 — libgen, then languages

The gated modules (`code_gen::rust_c_ffi`, `code_gen::rust_abi_stable`, all of
`lib_gen`) are **not a port**. They were written for the pre-G1a orchestration
model — they open `.frozen/` themselves (the store is `.comline/` now), call
`basic_storage::get_latest_version`, walk `package/versions/{v}/`. Reviving them
means **rewriting each as a pure function the CLI drives**, the way `code_gen`
works now: `(package metadata, [(namespace, &[FrozenUnit])], out dir) -> files`.

Three independent tracks:

#### G2a — `mode = "lib"` for plain rust ✅

Generation: generation#5 (contract + rust `Lib`) + generation#6 (`autobins`).
CLI: cli#17.

- Generator signature is `fn(&GenRequest) -> Result<Vec<GeneratedFile>>` (the
  [contract](#generator-output-contract) below).
- `rust` `Lib` returns `Cargo.toml` (`name` = congregation name, `version` =
  package version or `0.0.0`, `edition = "2021"`, `autobins = false`, `serde`
  only), `src/lib.rs` (the `pub mod` list), `src/<namespace>.rs`.
- CLI: `t.mode` → `Mode`; per version, one `GenRequest` with every schema; the
  returned files write under `<out>/<language>/` for `lib`, at `layout` for
  `code`. `dylib` is rejected.

No FFI, no compile step. Deliberately out of scope for now (each a documented
error or noted follow-up): nested (`/`-joined) namespaces in `lib`, multi-version
`lib`, `layout`-driven `lib` root, `typescript` `Lib`. A namespace literally
named `main` / `lib` compiles but trips Rust's `special_module_name` warning —
fix by nesting the schema modules under `src/schemas/`.

#### G2b — TypeScript in `code` mode (generation#4, comline-typescript#5, #8)

IR → `.ts` source: `export interface` per `struct`; per `error` an
`export interface` (wire payload) plus an `export class <Name>Error extends
Error` (`.data` + a static `.ordinal`); `export enum` with string values per
enum. A `protocol` emits the full RPC shape against `@comline/runtime` — an
`IR_HASH` bigint const (the canonical `schema_ir_hash`), `<Proto><Fn>Params`
interfaces, a provider interface of `Promise`-returning methods with `@throws`
JSDoc, a `<PROTO>_CALLS` table, a `<Proto>Dispatcher` (`implements Dispatch`), a
`<Proto>Client` (+ static `connect`, running the handshake), and a
`serve<Proto>` helper. Framing follows `@framing` / the package
`default_framing` (`DatagramFraming` default, `JsonRpcFraming` for `jsonrpc`).
Type map: `string`/`str` → `string`, `bool` → `boolean`, `u128`/`i128`/`s128`
→ `bigint`, every other int/float width → `number`, `T[]` → `T[]`, `optional`
→ `name?: type`, `()` → `void`.
`lib` mode (comline-typescript#9) wraps the per-schema `.ts` output in an npm
package — `package.json` (declaring `@comline/runtime`), `tsconfig.json`, a
`src/index.ts` barrel.

Lives as a module in `comline-codelib-gen` (`code_gen/typescript/`) alongside
`rust` for now; G3 moves it to `comline-typescript`. `lib-gen/typescript/` keeps
its `implementation plan.md` for the eventual TS `lib` / `dylib` side.

Registered under `typescript` and `ts`, version key `"5.0"`. No CLI change —
`find_generator` dispatch is generic; a target picks it up once `cli` bumps its
`comline-codelib-gen` rev.

#### G2c — FFI / abi_stable / `mode = "dylib"` — deferred

`code_gen::rust_c_ffi`, `code_gen::rust_abi_stable`, `lib_gen::rust_c_ffi`, and
`builder.rs` (which shells `cargo build --release`). Tied to the dormant runtime
dylib-loading story ([runtime structure](runtime-repo-structure.md)) and needs
core#8. Not scoped until that is. When it happens it lands in `comline-rust`, not
`generation`.

### G3 — split to per-language repos

G0–G2 got the generators out of `core` and into `generation` as pure,
CLI-driven functions. G3 takes them the rest of the way, per the
[repo decision](runtime-repo-structure.md):

1. **`generation` → `comline-codegen`.** ✅ Split into `comline-codegen` (the
   contract + a `Registry` type replacing the hardcoded static + `FrozenUnit`
   helpers) plus `comline-codegen-rust` / `comline-codegen-typescript` crates.
   The CLI composes a `Registry` at startup via each crate's `register()`.
2. **`comline-typescript`, `comline-rust`.** ✅ Both generators extracted to
   their own repos (`ComlineProject/comline-typescript`,
   `ComlineProject/comline-rust`); `cli` and `generation`'s conformance corpus
   depend on them by git rev. `generation` is now just `comline-codegen` +
   `comline-conformance`. `comline-rust`'s FFI/dylib work is still G2c.
3. **CLI features.** ✅ `comline-codegen-rust` / `-typescript` are optional deps
   behind `gen-rust` / `gen-typescript` (both default); `generator_registry()`
   `#[cfg]`-guards each `register()`. A build can drop a generator crate and its
   whole dependency tree. See [The registry](#the-registry).
4. Each further language is a new `comline-<lang>` repo from the template — zero
   change to the others.

Blocked on the prerequisites in the
[repo decision](runtime-repo-structure.md): the `core ↔ target` contract doc and
the conformance corpus (before the second target repo). No release step —
everything stays on git revs.

## Generator crate layout

The [repo decision](runtime-repo-structure.md) is one repo per target language,
so the generators do not consolidate in `generation` — each lands in its
`comline-<lang>` repo, next to that language's runtime.

- **`comline-codegen`** (what `generation` becomes) — the shared, neutral
  support crate: the contract, the `FrozenUnit` helpers, the `Registry` type.
  One dep (`comline-core`), no language-specific code.
- **`comline-<lang>/codegen`** — that language's `code` generator: pure string
  work over `FrozenUnit`, depends on `comline-codegen` + `comline-core`, nothing
  heavy. (A Python `code` generator emits `.py` text and never touches `pyo3`.)
- **`comline-<lang>/libgen`** — that language's `lib` / `dylib` generator, with
  the heavy ecosystem deps (`toml_edit`, pyproject writers, `cbindgen`, `pyo3`,
  `mlua`, `abi_stable`) — isolated in that one repo, invisible to every other
  target and to a consumer who only wants rust.

The old plan kept every `code` generator in one `comline-codelib-gen` crate
because `code` mode is light and "a crate per 20-line module is ceremony". That
still holds *inside* a target repo — `codegen` and `libgen` are modules/crates
within `comline-<lang>`, not separate repos. What changed is the outer boundary:
the languages no longer share a repo, so the CLI composes N repos.

### The registry

`find_generator` was a hardcoded `HashMap` in `comline-codelib-gen`. With the
generators in separate repos the CLI is the composition root:

- it depends on the `comline-<lang>` generator crates it enables, **behind cargo
  features** — `comline generate` built with only `--features rust` never
  compiles the TypeScript or Python generator or their deps;
- it builds the `Registry` at startup from the enabled crates;
- a third party ships `comline-elixir` from their own repo and a build opts in
  with `--features elixir`.

`comline-codegen` owns the `Registry` type and the contract; it depends on no
generator.

## Language version & dialect

`generation`'s `find_generator` selects by an exact `(language, version)` string
key — `rust::GENERATORS` has one entry, `"1.70.0"` — so `rust#1.75.0` or
`rust#1.70` gives "no generator". `core`'s old one ignored the version arg
entirely. Neither is right: that one string is standing in for several
independent things, and how many differs per language.

| Language | "how new can syntax be" (monotonic) | non-monotonic dialect axis |
|---|---|---|
| Rust | release — `1.75` (`async fn` in traits, `let`-else) | **edition** 2015 / 2018 / 2021 / 2024 |
| Python | interpreter — `3.12` (`type` stmt, `X \| Y`, `match`) | — |
| TypeScript | lang version — `5.4` (`satisfies`, `const` type params) | **`target`** ES2015…ESNext, **`module`** CJS/ESM/NodeNext |
| Luau | Roblox release | — |
| C | — | **`std`** — c89 / c99 / c11 / c23 *is* the whole axis |
| Go | `go 1.21` line (generics @1.18) — monotonic | — |

So: some languages have zero axes that matter (defaults are fine), most have
one, Rust and TypeScript have two or more, and for C the "version" *is* a
dialect. No single fixed schema fits.

**No language actually selects a different *generator* by version.** `rustc` is
one binary that takes `--edition`; `tsc` takes `--target` / `--module`; `gcc`
takes `-std=`. Version / edition / target are generator **configuration**, not
generator **selection**.

**Proposed shape:**

- `find_generator` keys on **language name only** — one generator per language.
- The language declaration carries an **`options` string-map** — opaque to
  `core`, the IR, and the CLI; meaningful to that generator, which documents and
  validates its own keys:

  ```
  rust    { edition = "2021", min_version = "1.75" }
  python  { min_version = "3.12" }
  ts      { target = "ES2022", module = "ESNext" }
  c       { std = "c11" }
  (most)  { }
  ```

- The container is uniform (`Map<String, String>` frozen verbatim into the IR);
  the contents are the generator's contract. A new TypeScript option later
  touches only the TypeScript generator — not `core`, the IR, or the CLI.
- `rust#1.70.0` becomes sugar for / is replaced by `rust = { … }` in
  `config.idp`.
- Feeds G2a: the rust generator's `options.edition` is exactly what the
  generated `Cargo.toml` needs.

A patch/minor bump alone almost never changes output (struct / enum / trait +
serde are stable across Rust 1.x), so a generator reads these only for the
specific constructs that need them — none do yet.

## Generator output contract

**Today a generator returns one string** — one file's worth of source for one
schema. The CLI picks the filename (from `comline.toml` `layout`) and writes it.
Fine for `mode = "code"`: "give me the types as source I'll paste in."

**`mode = "lib"` asks for a whole buildable package, not a snippet.** A Rust
package is a small folder, not one file:

```
Cargo.toml       project settings — name, version, the serde dependency
src/lib.rs       an index: "there is a module `message`, a module `user`"
src/message.rs   the code for one schema
src/user.rs      …and the next
```

A function that returns *one string* can't hand back a folder of different
files. Some of those files (`Cargo.toml`, `src/lib.rs`) also aren't "one
schema's code" at all — `lib.rs` lists *every* schema, so the generator needs
them all in view, not one at a time.

**Landed (generation#5): a generator returns a list of files.**

```rust
struct GeneratedFile { path: PathBuf, contents: String }   // relative to the output root
enum   Mode { Code, Lib }
struct GenRequest<'a> {
    mode: Mode,
    schemas: &'a [(String, Vec<FrozenUnit>)],               // every namespace + its IR
    package: PackageMeta,                                    // name, version — for the Lib manifest
}
type GeneratorFn = fn(&GenRequest) -> Result<Vec<GeneratedFile>>;
```

- `mode = "code"` → one file per schema (the old string, wrapped).
- `mode = "lib"` → `Cargo.toml`, `src/lib.rs`, the per-schema files.
- The generator sees **all** schemas (for `src/lib.rs`) and returns paths; the
  CLI writes the list — one loop, both modes.

These three types (`GeneratedFile` / `Mode` / `GenRequest`) are the contract
`comline-codegen` will own after G3; today they live in `comline-codelib-gen`.

Settled with it:

- **Paths.** `layout` places the single `code` file; a `lib` crate goes under
  `<out>/<language>/` and the crate's insides (`Cargo.toml`, `src/…`) are the
  generator's. (`layout`-driven `lib` root is a follow-up.)
- **No file "kind" tag** — `comline clean` can ask the generator "what paths
  would you write?" rather than tag each file. `clean.rs` is unchanged so far;
  its "dedicated `out` dir → remove wholesale" branch covers the common `lib`
  config.
- **Text only** — `contents: String`.

The CLI side (`generate.rs`) landed in cli#17.

## Open questions

- **Git revs, not releases** — decided. `generation` → `core`, `cli` → both, and
  every `comline-<lang>` → `comline-core` + `comline-codegen` stay on git revs.
  Every `core` IR change means a coordinated rev bump across the consuming repos.
  Publishing to crates.io is a later call, taken if that coordination gets
  painful — it slots in without reordering anything.
- **First `comline-<lang>` repos: `comline-rust` and `comline-typescript`** —
  the two generators that exist. `comline-typescript` is the cleaner pilot
  (`code` mode only, no runtime, no FFI). `comline-python` / `comline-lua` /
  `comline-luau` follow, each from the template.
