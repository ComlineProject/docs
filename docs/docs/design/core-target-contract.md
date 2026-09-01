# The `core` ↔ target contract

Status: **draft** — surfaces 1–3 (schema IR, config IR, codegen contract) are
solid and ready to build a `code` generator on; surface 4 (runtime API +
generated protocol) has a worked design in §4 with named decisions still open ·
Affects `ComlineProject/core`, `ComlineProject/generation`,
`ComlineProject/runtime`, `ComlineProject/comline-<lang>`, `ComlineProject/cli`

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
| 4 | **Core-runtime API + generated protocol** — `CallSystem`, `Dispatch`, `WireFormat`, the per-protocol codegen | `runtime`: `comline-runtime` (`setup/`, `package_abi/`) | link the per-language runtime against; shape the generated client / dispatcher | **worked design, §4** |
| 5 | **FFI / dylib ABI** — `PackageLib` root module | `runtime`: `package_abi/interface.rs` (`abi_stable`) | load a compiled package at run time | **exists, deferred** |

Surfaces 1–3 are what a `code` generator needs and are ready to build on now.
Surface 4 is what a *runtime* / `lib` generator needs; §4 works it out in full
with the open decisions named. Surface 5 is parked with
[G2c](generation.md#g2-libgen-then-languages) until the runtime dylib story and
core#8 land.

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

## 4 — Core-runtime API and the generated protocol

This is the least settled surface, and it gates `comline-rust` — *not*
`comline-typescript`, which is `code`-only and needs none of it. What follows is
the **working design**, not a finished contract: §4.1 is what the runtime code
already commits to, §4.2–4.3 the proposed shape, §4.4 the decisions (one pinned,
the rest still to design).

### 4.1 — What the runtime already commits to

In `comline-runtime` (`runtime` repo), bodies are `todo!()` but the shapes exist:

- **Three layers, cleanly separated.** Transport (`CommunicationConsumer` /
  `CommunicationProvider` — byte streams, `methods::tcp`) → call system
  (`CallSystem`: `receive_data` / `send_data`; framing lives in `systems::` —
  `JsonRPCv2`, `xml_rpc`) → generated code.
- **Args are a serde value, not `dyn Any`.** `CallSystemConsumer::send_async_call<M>`
  and `AbstractCall<M>` take `M: Serialize + DeserializeOwned`. The
  `Message` / `Parameter(&dyn Any)` in `setup/abstract_call.rs` is vestigial and
  should be deleted.
- **Consumer and provider are distinct traits**, both `: CallSystem`. Builder
  setup: `ConsumerSetup::with_transport(t).with_call_system(|o| JsonRPCv2::new(o))`.
- **`CallProtocolMeta` is metadata only** — `calls_names() -> &'static [&'static str]`,
  `call_name_from_id(u16)` (indexes that slice), `make_call(params) -> AbstractCall`.
- **Async-first** — tokio, `watch` channels, `async_trait` on the transport traits.

Known-wrong bits, to fix as part of this design:

- `send_async_call<M>` uses **one type parameter for request *and* response**.
- `CallResult<T> = Result<T, ()>` — no real error type.
- `JsonRPCv2` hard-codes `serde_json`.
- `Kind::Id(u16)` is a bare index into `calls_names()`.

### 4.2 — The generated protocol (proposed)

For `protocol Chat { function send(msg: Msg) -> Ack ! Rejected; function history(limit: u32) -> Msg[]; }`:

```rust
// 1. one params struct per function — this is struct codegen, reused
#[derive(Serialize, Deserialize)] struct ChatSendParams   { msg: Msg }
#[derive(Serialize, Deserialize)] struct ChatHistoryParams { limit: u32 }

// 2. one error enum per function: its `! Errors` plus a runtime variant
enum ChatSendError    { Rejected(Rejected), Runtime(RuntimeError) }
enum ChatHistoryError { Runtime(RuntimeError) }

// 3. provider trait — the user implements this
trait Chat {
    async fn send(&self, msg: Msg) -> Result<Ack, ChatSendError>;
    async fn history(&self, limit: u32) -> Result<Vec<Msg>, ChatHistoryError>;
}

// 4. consumer stub — generated, wraps a CallSystemConsumer
struct ChatClient<C> { cs: C }
impl<C: CallSystemConsumer> ChatClient<C> {
    async fn send(&mut self, msg: Msg) -> Result<Ack, ChatSendError> {
        self.cs.call(Kind::Id(0), &ChatSendParams { msg }).await   // decodes the ok/err envelope
    }
    // history → Kind::Id(1) …
}

// 5. dispatcher — generated, implements the new runtime `Dispatch` trait
struct ChatDispatcher<T: Chat> { inner: T }
impl<T: Chat> Dispatch for ChatDispatcher<T> {
    async fn dispatch(&self, call: Kind, params: &[u8], fmt: &dyn WireFormat)
        -> Result<Vec<u8>, RuntimeError>
    {
        match call.index(Chat::CALLS)? {
            0 => envelope(self.inner.send(fmt.decode::<ChatSendParams>(params)?.msg).await, fmt),
            1 => envelope(self.inner.history(fmt.decode::<ChatHistoryParams>(params)?.limit).await, fmt),
            _ => Err(RuntimeError::UnknownCall),
        }
    }
}

// 6. impl CallProtocolMeta for the marker type — calls_names() in declaration order
```

Everything here is mechanical over the `Protocol` / `Function` IR. The only
inputs a generator needs beyond what it already reads for structs are the
runtime trait names (`CallSystemConsumer`, `Dispatch`, `WireFormat`,
`RuntimeError`) — which is exactly what this section pins down.

### 4.3 — Runtime additions this needs

| Add | Shape | For |
|---|---|---|
| `RuntimeError` | `enum { Transport, Serialization, Framing, Timeout, UnknownCall, Remote(RemoteError) }` | replace `Result<T, ()>` everywhere |
| `trait Dispatch` | `async fn dispatch(&self, Kind, &[u8], &dyn WireFormat) -> Result<Vec<u8>, RuntimeError>` | the provider call system holds `Arc<dyn Dispatch>` and routes inbound frames to it |
| `CallSystemConsumer::call<P, R>` | `async fn call<P: Serialize, R: DeserializeOwned>(&mut self, Kind, &P) -> Result<R, RemoteError>` | replaces `send_async_call<M>` (the one-type-param bug) |
| `trait WireFormat` | `encode<T: Serialize>(&T) -> Vec<u8>` / `decode<T: DeserializeOwned>(&[u8]) -> Result<T, _>` | the serialization axis; call systems are generic over / configured with one |
| wire envelope | `{ ok: R }` \| `{ err: { name: String, body: <error> } }` | carry a named thrown error back to the client stub |

### 4.4 — Decisions

#### Call addressing — **pinned: append-only declaration order**

A function's id is its index in `calls_names()`, i.e. its position in the
`protocol` block. Protocol functions are **append-only**: a removed function is
deprecated in place, its slot never reused; a new function is appended. This is
the protobuf field-number / Cap'n Proto ordinal discipline, and Comline's CAS +
[automatic versioning](../reference/versioning.md) is what enforces it (a
reorder or a slot reuse is a detectable breaking change). `Kind::Named` stays on
the wire for debuggability and for framings that are name-oriented (JSON-RPC);
`Kind::Id` is the compact form.

#### Error grouping — leaning per-function, needs polish

Per-function (`ChatSendError`) over per-protocol (`ChatError`): the enum then
lists exactly that function's `! Errors` plus `Runtime(RuntimeError)`, so an
exhaustive `match` at the call site is precise. Open:

- **Name-only `throws`.** The IR's `throws: Vec<String>` is a bare reference; the
  generator maps each name to `Variant(NamedErrorStruct)` and a decode arm keyed
  on the envelope's `err.name`. The [schema](../guide/idl/error.md) can't yet
  bind field values at the raise site — but the generated Rust *impl* returns a
  fully-built error value, so this doesn't block codegen.
- **`RemoteError` shape.** What the client reconstructs from `err` when the name
  isn't one the local generated code knows (peer newer than us): a catch-all
  `Runtime(RuntimeError::Remote { name, raw })`.
- Whether the per-protocol union is *also* emitted, for callers that want one
  `match`.

#### `synchronous` / one-way — needs design

The IR carries **both** `Function.synchronous: bool` **and**
`Function._return: Option<KindValue>`, and the [guide](../guide/idl/protocol.md)
says "omit [the return] for a one-way call" (`function poke();`). That's a
redundancy to resolve. Proposal:

- **One-way ⟺ `_return == None`.** No response frame (a JSON-RPC notification —
  no `id`), and `! Errors` is rejected by the compiler on such a function
  (nowhere to deliver them). This is a wire-level fact and travels.
- **Blocking vs async is a *binding* concern, not a protocol one.** The
  generated trait is always `async`; whether the client *also* gets a blocking
  wrapper is a generator option with a per-language default (Rust: async; Python:
  blocking). It does not travel and is not `synchronous`.
- Which leaves **`synchronous` with no job** — candidate for removal from the IR,
  unless it's meant to express something the return type can't (e.g. "the caller
  must observe completion even though there's no value" — a `-> ()` that still
  gets an ack). Needs a call.

#### Serialization — a `WireFormat` trait, needs design

`JsonRPCv2` hard-codes `serde_json`; the [call-system guide](../guide/runtime/call-system.md)
frames framing and message serialization as *two* pluggable axes. A `WireFormat`
trait (§4.3) keeps the generated code `serde`-only and picks the encoder at
setup. The tension to design through: a framing like JSON-RPC assumes a JSON
payload, so "MessagePack inside JSON-RPC" isn't free — either the framing is
also generic over `WireFormat` (JSON-RPC-with-msgpack-params via base64/bytes),
or framings declare which formats they accept and the setup is checked.

#### Per-call settings — needs architecture

The schema allows `@timeout_ms=1000` on a function
([guide](../guide/idl/protocol.md)); the runtime has
`AbstractCall.settings: &'static [(&'static str, &'static Setting)]` with
`Setting::{ None, Num(usize), Str(&'static str) }`. But **`FrozenUnit::Function`
has no annotations slot today** — `Struct` / `Field` / `Protocol` carry
`parameters: Vec<FrozenUnit>`, `Function` does not — so there is no IR source for
these. Order of work: (1) add function annotations to the IR, (2) decide the
knob set (timeout, retry?, priority?) and its types, (3) consumer-side override
vs schema-declared default. Deferred from the generated path until (1).

### 4.5 — Still open beyond the above

- **The per-language-runtime ↔ core-runtime seam.** The
  [runtime guide](../guide/runtime/index.md) says each language has a "thin
  runtime that speaks to the core runtime" — that trait boundary is nowhere yet.
  For Rust it's degenerate (the target repo *is* Rust); it becomes real with the
  second `lib`-mode language.
- **Streaming / server-push.** `Event<Incoming, Outgoing>` and the `watch`
  plumbing hint at it; no design. A `function` returning a stream has no IR
  representation.
- **`no_std` runtime.** `comline-runtime` is `std` + nightly today; the
  `core_no-std` fork is slated to become a feature (repo decision), which this
  API has to stay compatible with.

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

## Where this is unresolved

Surfaces 1–3 are ready to build a `code` generator on now (`comline-typescript`,
rollout step 4). The live design work is all in **surface 4**:

- §4.4 — error grouping, `synchronous` / one-way, the `WireFormat` axis,
  per-call settings (each needs a decision before `comline-rust`, step 5).
- §4.5 — the per-language-runtime seam, streaming, `no_std`.
- §5 — the FFI ABI, parked with G2c.

Smaller, outside surface 4: float primitives are commented out in `core`
(surface 1); whether the schema IR gets an explicit `FrozenUnit::IrVersion`
(Versioning, above).
