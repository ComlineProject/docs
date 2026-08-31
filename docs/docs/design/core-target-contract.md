# The `core` ↔ target contract

Status: **draft** — first cut; the schema/config IR and the codegen contract are
solid, the runtime API is early · Affects `ComlineProject/core`,
`ComlineProject/generation`, `ComlineProject/runtime`,
`ComlineProject/comline-<lang>`, `ComlineProject/cli`

Under the [repo decision](runtime-repo-structure.md), every `comline-<lang>` repo
builds against `comline-core` and `comline-codegen` — nothing else from the org.
This page writes down that boundary. It is **step 2 of the rollout** and gates
the second target repo: once two repos depend on the contract, a change to it is
a coordinated bump across all of them, so it has to be a named, deliberate thing.

Everything is consumed **by git rev** (no crates.io — see the repo decision), so
"versioning the contract" here means a discipline, not a registry.

## The surfaces

The contract is five distinct surfaces, at very different maturity:

| # | Surface | Defined in | A target repo uses it to… | Maturity |
|---|---|---|---|---|
| 1 | **Schema IR** — `FrozenUnit`, `KindValue` | `core`: `schema/ir/frozen/unit.rs`, `…/interpreted/kind_search.rs` | drive the code generator | **stable-ish** |
| 2 | **Config IR** — `FrozenUnit` (config) | `core`: `package/config/ir/frozen/mod.rs` | fill in a `Lib` build's manifest | **stable** |
| 3 | **Codegen contract** — `GenRequest`, `GeneratedFile`, `Mode`, `PackageMeta` | `comline-codegen` (today `comline-codelib-gen`) | be invoked by the CLI | **stable** |
| 4 | **Core-runtime API** — `CallSystem`, transport traits, `CallProtocolMeta`, `Message` | `runtime`: `comline-runtime` (`setup/`, `package_abi/`) | link the per-language runtime against | **early** |
| 5 | **FFI / dylib ABI** — `PackageLib` root module | `runtime`: `package_abi/interface.rs` (`abi_stable`) | load a compiled package at run time | **exists, deferred** |

Surfaces 1–3 are what a `code` / `lib` generator needs and are ready to build
on. Surface 4 is the one a *runtime* needs, and it is a sketch. Surface 5 is
parked with [G2c](generation.md#g2-libgen-then-languages) until the runtime
dylib story and core#8 land.

## 1 — Schema IR

A compiled schema is `Vec<FrozenUnit>` (`serde`, `Debug + Eq + Clone`). One unit
per declaration; see the [IR guide](../guide/ir/index.md) for the reader's view.
The variants a generator will actually match on:

- `Namespace(String)`, `Name(String)`
- `Struct { docstring, parameters, name, fields, span }` — `fields` are `Field`
- `Field { docstring, parameters, optional, name, kind_value, span }`
- `Enum { docstring, name, variants, span }` — `variants` are `EnumVariant(KindValue, span)`
- `Protocol { docstring, parameters, name, functions, span }` — `functions` are `Function`
- `Function { docstring, name, synchronous, arguments, _return, throws, span }`
  — `arguments` are `FrozenArgument { name, kind, span }`, `_return` is
  `Option<KindValue>`, `throws` is `Vec<String>` (names, unresolved)
- `Error { docstring, parameters, name, message, fields }`
- `Constant { docstring, name, kind_value, span }`
- `Validator`, `ValidatorRef`, `ExpressionBlock`, `Assert`, `Settings` — the
  [validators](validators.md) surface; a `code` generator can ignore all of
  these, a `lib` generator that enforces validation cannot

### Types — `KindValue`

Every typed slot (`Field.kind_value`, `FrozenArgument.kind`, `Function._return`,
`Constant.kind_value`) is a `KindValue`:

```rust
enum KindValue {
    Primitive(Primitive),                       // bool, u8..u128, s8..s128, String, Namespaced
    EnumVariant(String, Option<Box<KindValue>>),
    Union(Vec<KindValue>),
    Namespaced(String, Option<Box<KindValue>>), // a reference to another declared type
}
```

`Primitive` carries an optional literal value (its default). Widths are explicit
(`u8`…`u128`, `s8`…`s128`); there is no bare `int`. Float variants are commented
out in `core` today — **a generator must not assume `f32`/`f64` exist yet**.
Mapping this enum to a language's type system is the bulk of a `code` generator
and is worked in [Codegen by language](codegen-by-language.md).

### Stability

Recently through an "audit IR" pass (spans added to most variants and folded
into CAS identity; `Import` gained the alias slot; validators phase 3 landed).
Not frozen, but changes now are deliberate. **A generator should match
exhaustively and fail loudly on an unknown variant**, not silently skip.

## 2 — Config IR

The package manifest (`congregation`) lowers to its own `Vec<FrozenUnit>`
(`package/config/ir/frozen/mod.rs`):

```rust
enum FrozenUnit {
    Namespace(String),
    SpecificationVersion(u8),
    PackageVersion(String),
    SchemaPath(String),
    Dependency(Dependency { author, project, version }),
    CodeGeneration(LanguageDetails { name }),          // a declared target language
    PublishRegistry((String, PublishRegistry { kind, uri })),
}
```

A `lib` generator reads `PackageVersion` and `Namespace` for the manifest it
emits (`Cargo.toml`, `pyproject.toml`, …). `CodeGeneration` is a *capability
declaration* — "this package supports being generated as `rust`" — not consumer
config; where the code lands is the consumer's `comline.toml`.
`SpecificationVersion` is the manifest format version (`u8`, currently `1`).

## 3 — Codegen contract

How the CLI drives a generator (`comline-codegen`; landed generation#5):

```rust
struct GeneratedFile { path: PathBuf, contents: String }   // relative to the target's output root
enum   Mode { Code, Lib }
struct PackageMeta { name: String, version: String }
struct GenRequest<'a> {
    mode:    Mode,
    schemas: &'a [(String, Vec<FrozenUnit>)],   // every namespace in the package + its schema IR
    package: PackageMeta,
}
type GeneratorFn = fn(&GenRequest) -> Result<Vec<GeneratedFile>>;
```

- `Mode::Code` → one source file per schema. `Mode::Lib` → a buildable package
  (manifest + module tree). `dylib` is not in `Mode` yet (G2c).
- The generator sees **all** schemas at once (it needs them for the `lib`
  index file) and returns a flat file list; the CLI writes it — one loop, both
  modes.
- Text only (`contents: String`). No binary artifacts, no post-generate compile
  step in the contract.

This is the crisp part of the boundary. See
[Generator output contract](generation.md#generator-output-contract) for the
history and the settled edges (paths, `comline clean`, no file-kind tag).

## 4 — Core-runtime API

What a per-language runtime links against, in `comline-runtime` (`runtime`
repo). This is **early** — nightly features, placeholder error types — and is
the surface most likely to move.

- `CallSystem` trait — `receive_data(&[u8])`, `send_data(&[u8])`,
  `add_event_listener(EventType)`. Pluggable framing (`systems::json_rpc`,
  `systems::xml_rpc`).
- `CallSystemConsumer` / `CallSystemProvider`, built via `CallSystemBuilder`.
- `CallProtocolMeta` — `calls_names() -> &'static [&'static str]`,
  `call_name_from_id(u16)`, `make_call(params) -> AbstractCall`. The generated
  code implements this per protocol.
- `Kind::{ Id(u16), Named(String) }` — a call is addressed by index or by name.
- `Message` / `Parameter` (`setup/abstract_call.rs`) — parameter carrier;
  `Deserialize` is stubbed out.
- Transport: `CommunicationConsumer` / `CommunicationProvider`,
  `methods::tcp`.
- `CallResult<T> = Result<T, ()>` — **placeholder**; a real error type is
  pending.

### What the generated code is expected to produce

Per [Library generation](../guide/codegen/library-generation.md): a `lib` build
emits the schema *types* plus a `CallProtocolMeta` impl per protocol, and links
`comline-runtime` for dispatch. The exact trait a generated protocol impl must
satisfy is **not pinned yet** — this is the main gap this doc can't close until
the runtime firms up.

## 5 — FFI / dylib ABI

`package_abi/interface.rs`, `abi_stable`:

```rust
#[sabi(kind(Prefix(prefix_ref = PackageLibRef)))]
struct PackageLib {
    to_message: extern "C" fn(data: RVec<u8>) -> MessageBox,
}
// RootModule: BASE_NAME = NAME = "package_lib"
load_root_module(directory: &Path) -> Result<PackageLibRef, LibraryError>
```

A compiled package is a `cdylib` exposing `package_lib`; the host loads it and
calls `to_message`. Deferred with [G2c](generation.md#g2-libgen-then-languages)
— it needs the runtime dylib-loading story and core#8. Listed here so a target
repo knows the shape it will eventually target.

## Versioning the contract

Git revs, so there is no semver gate — the discipline is:

- **`FrozenUnit` changes are additive by default.** A new variant, or a new
  field on a struct-like variant behind `#[serde(default)]`, lets an older
  generator keep working. A rename or a removed field is a breaking change and
  needs every `comline-<lang>` rev-bumped in lockstep.
- **One `comline-core` per tree.** The CLI composes N target generators; they
  must all pin the same `comline-core` rev (the constraint already hit between
  `generation` and `cli`). A contract change = bump `core`, then bump every
  consumer to that rev in one pass.
- **`SpecificationVersion` covers the manifest only.** It does not version the
  schema IR or the runtime API. If the schema IR needs an explicit version,
  add a `FrozenUnit::IrVersion(u16)` rather than overloading the spec version.
- **The CAS makes each frozen commit self-describing** — a stored version
  records the IR that produced it, so old versions stay readable even as the
  live `FrozenUnit` moves. Cross-version *generation* still needs the generator
  to handle the older shape; the corpus (rollout step 3) is where that's
  checked.

## Open questions

- **The generated-protocol trait.** Surface 4 can't be nailed down until
  `comline-runtime` says exactly what a generated `Protocol` impl must provide
  (beyond `CallProtocolMeta`) and how `Function.throws` / `_return` /
  `synchronous` map onto it.
- **A real runtime error type.** `CallResult<T> = Result<T, ()>` has to become
  a defined error before any target repo can build a non-toy runtime.
- **Message serialization.** `Message` / `Parameter` deserialization is stubbed;
  the "message serialization" axis of the [call system](../guide/runtime/call-system.md)
  is still a plan.
- **Per-language runtime ↔ core-runtime seam.** The guide says each language has
  a "thin runtime that speaks to the core runtime" — that trait boundary isn't
  written down anywhere yet, and it belongs in this doc once it exists.
- **Async.** `Function.synchronous: bool` is in the IR; nothing downstream acts
  on it.
