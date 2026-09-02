# The `core` ↔ target contract

Status: **draft** — surfaces 1–3 (schema IR, config IR, codegen contract) are
solid and ready to build a `code` generator on; surface 4 (runtime API +
generated protocol) has a worked design in §4 — `no_std`-first, borrowed
generated types, memory configured once at setup, a zero-alloc call budget and a
hardening baseline (§4.6), and every §4.4 decision (call addressing, error
grouping, `synchronous` / one-way, transport / framing / format, per-call
settings) made. §4.3's trait-level types are built in `comline-runtime`'s
`contract` module, with a MessagePack `WireFormat` (7b) and an end-to-end
`Dispatch` round-trip test proving the surface fits (7c). The stubbed `setup/`
layer is replaced by real `wire` (framing) + `transport` (`Transport` trait,
`InMemory` + `Tcp` impls) + `serve` (`Server<D, W>`) + `client` (`Client<T, W>`)
modules (7d–7e), tested end to end over both transports. The §4.4 IR changes are
landed in `comline-core` (drop `synchronous`, `Function.parameters`,
`KindValue::Unit` — core#46; `throws: Vec<u16>` + error ordinals — core#47).
Pluggable framing with a JSON-RPC impl (runtime#10 + comline-rust#8), the
per-`protocol` `@framing` selector (comline-rust#9), and the `comline.toml`
package-wide `default_framing` (generation#17 + comline-rust#10 + cli#27) are
built. Open: the `Alloc` seam, the async layer (7f+) ·
Affects
`ComlineProject/core`, `ComlineProject/generation`, `ComlineProject/runtime`,
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
| 4 | **Core-runtime API + generated protocol** — `Dispatch`, `WireFormat`, `wire` / `transport` / `serve`, the per-protocol codegen | `runtime`: `comline-runtime` (`contract/`, `format/`, `wire`, `transport`, `serve`, `package_abi/`) | link the per-language runtime against; shape the generated client / dispatcher | **worked design, §4; contract + serve path built** |
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
- `Function { docstring, parameters, name, arguments, _return, throws, span }`
  — `arguments` are `FrozenArgument { name, kind, span }`, `_return` is
  `Option<KindValue>` (`None` ⟹ one-way, `Some(KindValue::Unit)` ⟹ empty ack,
  §4.4); `throws` is `Vec<u16>` — schema-global error ordinals resolved at
  freeze; `parameters` are `Property { name, expression }` from `@key=value`
  function annotations. (`synchronous` dropped — core#46; `throws`/ordinals —
  core#47.)
- `Error { docstring, parameters, ordinal, imported_from, name, message, fields }`
  — `ordinal` is this error's schema-global slot (the `u16` in the envelope's
  `err` id); `imported_from` is `Some(ns)` when the unit is a re-export slot
  for a `use`d foreign error a `throws` names (`<unresolved: Name>` if it
  couldn't be located), `None` for a local `error`
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
out in `core` today — **a generator must not assume `f32`/`f64` exist yet**. A
`Unit` variant is slated (for `-> ()`, §4.4). Mapping this enum to a language's
type system is the bulk of a `code` generator and is worked in
[Codegen by language](codegen-by-language.md).

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

Slated: a **transport-requirements** unit (`reliable` / `ordered` / `duplex` /
`max_message_bytes` / one-way delivery-ack), the same capability-declaration
kind as `CodeGeneration`, read by the runtime at connect time (§4.4).

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

In `comline-runtime` (`runtime` repo), after rollout steps 7a–7e the shapes are
built and tested (no more `todo!()` on this path):

- **Three layers, cleanly separated.** Transport (`transport::Transport` —
  frame-oriented `send` / `recv`, sync; `InMemory` mpsc + `Tcp` length-prefixed
  stream impls) → framing (`wire` — `[call_id][request_id][params]` request,
  `[request_id]` + `Envelope` response) → generated code (a `Dispatch` impl on
  the provider via `serve::Server`, a stub over `client::Client` on the
  consumer).
- **Args are a serde value, not `dyn Any`.** `WireFormat::{encode, decode}` take
  `T: Serialize` / `T: Deserialize<'de>`; the old `Message` / `Parameter(&dyn Any)`
  dynamic path is gone.
- **The serialization axis is a trait.** `WireFormat`; `format::MsgPack` is the
  first impl. Nothing hard-codes `serde_json`.
- **Request / response, not one type parameter.** `Client::call<P>(call_id, &P)`
  returns `(Envelope<'_>, &W)` — the generated stub decodes `Ok` as `R` or maps
  an `Err` ordinal to its schema-error enum, all under one `&mut self` borrow
  (one call outstanding; pipelining is additive).
- **Sync core.** No `async_trait`, no tokio on the contract path — an async layer
  sits behind the `std` feature and is emitted additively (§4.6).
- **`Kind`** carries either an `Id(u16)` (index into the protocol's call list) or
  a `Named(&'static str)`; `Kind::resolve(&[&str])` maps either to an ordinal.

**Framing is a pluggable axis** (built — [runtime#10](https://github.com/ComlineProject/runtime/pull/10) + [comline-rust#8](https://github.com/ComlineProject/comline-rust/pull/8)). `contract::Framing` is orthogonal to `WireFormat` — `Client<T, W, F>` / `Server<D, W, F>` are generic over one, default `DatagramFraming`. `framing::JsonRpcFraming` (std) is the name-oriented alternative: `{"jsonrpc":"2.0","method":…,"params":…,"id":N}`, a raised schema error → a JSON-RPC `error` object keyed by ordinal, pairs with `format::Json`. `Dispatch` writes into a `Reply` (framing-agnostic ok/err/none) instead of an `Envelope` buffer, and exposes `calls()` so a method name resolves to an ordinal; the generated stub passes `Call::new(id, name)` (both addresses, the framing picks).

**A schema selects its framing** ([comline-rust#9](https://github.com/ComlineProject/comline-rust/pull/9)). `@framing = "jsonrpc"` on a `protocol` (frozen into `Protocol.parameters` as a `Property`, same path as `@timeout_ms` / `@provider` — no core change) makes the generator emit the JSON-RPC stack instead of the datagram one: `<Proto>Client` wraps `Client<T, W, JsonRpcFraming>`, `connect` / `serve` call `Client::connect_with_framing` / `Server::with_framing`, and the `Handshake` carries `framing.name()` rather than `FRAMING_DATAGRAM`. Absent / unrecognised keeps the datagram default byte-for-byte. Recognised: `jsonrpc`, `json-rpc`, `jsonrpc-2.0`, plus `datagram` to opt a single protocol back out.

**A package-wide default** ([generation#17](https://github.com/ComlineProject/generation/pull/17) + [comline-rust#10](https://github.com/ComlineProject/comline-rust/pull/10) + [cli#27](https://github.com/ComlineProject/cli/pull/27)). `comline.toml`'s `[generate] default_framing` (per-`[[generate.target]]` overridable) rides `GenRequest.default_framing` to the generator and applies to every protocol with no `@framing` of its own. Resolution is `@framing` → package default → datagram. The contract crate treats the value as an opaque name; the target generator validates it.

Still open, to fix as part of this design:

- The `Alloc` seam for owned bits (`.to_owned()`, decoded collection spines).
- The async (`std`) layer — `AsyncDispatch` + an executor, emitted additively.

### 4.2 — The generated protocol

*Built for Rust — `comline-codegen-rust`'s `code` / `lib` output ([comline-rust#2](https://github.com/ComlineProject/comline-rust/pull/2)); a `tests/compiles.rs` generates a protocol crate and `cargo build`s it against `comline-runtime`. The full pipeline is exercised end to end in `cli` ([cli#24](https://github.com/ComlineProject/cli/pull/24)): a `.comline` schema → the real `comline generate` binary → the crate compiled against `comline-runtime` → a `ChatClient` ⇆ `ChatDispatcher` round-trip over `duplex()` (request/response, a typed raised error, a one-way notify).*

- **Borrowed str args** ([comline-rust#3](https://github.com/ComlineProject/comline-rust/pull/3)) — a `str` arg decodes borrowed: `<Proto><Fn>Params<'a> { #[serde(borrow)] name: &'a str }`, trait/client take `&str`. Array-of-string args, nested struct args and all return/data types are still owned (threading `<'a>` through the data types forces an owned/borrowed split on returns).
- **One-way** ([comline-rust#4](https://github.com/ComlineProject/comline-rust/pull/4) + [runtime#6](https://github.com/ComlineProject/runtime/pull/6)) — `_return: None` generates fire-and-forget: trait method `fn f(&self, …);` (no `Result`, no error enum), the dispatcher writes no `Envelope`, the client method is `-> Result<(), RuntimeError>` over `Client::notify`. `_return: Some(KindValue::Unit)` stays request/response with an empty ack.
- **Still open** — `Function.parameters` (per-call settings like `@timeout_ms`) not consumed; needs a runtime timeout mechanism first.

For `protocol Chat { function send(msg: Msg) -> Ack ! Rejected; function history(limit: u32) -> Msg[]; }`:

```rust
// 1. one params struct per function — this is struct codegen, reused
#[derive(Serialize, Deserialize)] struct ChatSendParams   { msg: Msg }
#[derive(Serialize, Deserialize)] struct ChatHistoryParams { limit: u32 }

// 2. one *schema-only* error enum per function — its `! Errors`, no runtime types (§4.4)
enum ChatSendError    { Rejected(Rejected) }
enum ChatHistoryError { /* no `!` → empty */ }
// + a per-protocol union, additive, for one broad handler:
enum ChatError { Rejected(Rejected) /* ∪ every `!` in Chat */ }
impl From<ChatSendError> for ChatError { /* … */ }

// 3. provider trait — the user implements this; schema errors only (sync core; async is additive, §4.6)
trait Chat {
    fn send(&self, msg: Msg<'_>) -> Result<Ack, ChatSendError>;
    fn history(&self, limit: u32) -> Result<Vec<Msg<'static>>, ChatHistoryError>;
}

// 4. consumer stub — wraps a CallSystemConsumer; CallError<E> adds infra failure
struct ChatClient<C> { cs: C }
impl<C: CallSystemConsumer> ChatClient<C> {
    fn send(&mut self, msg: Msg<'_>) -> Result<Ack, CallError<ChatSendError>> {
        self.cs.call(Kind::Id(0), &ChatSendParams { msg })   // encodes into a reused buffer,
    }                                                        // decodes the ok/err envelope borrowed
    // history → Kind::Id(1) …
}

// 5. dispatcher — generated, implements the runtime `Dispatch` trait
struct ChatDispatcher<T: Chat> { inner: T }
impl<T: Chat> Dispatch for ChatDispatcher<T> {
    fn dispatch<W: WireFormat>(&self, call: Kind, params: &[u8], fmt: &W, out: &mut dyn BufMut)
        -> Result<(), RuntimeError>
    {
        match call.resolve(Chat::CALLS).ok_or(RuntimeError::UnknownCall)? {  // index jump table
            0 => { let p: ChatSendParams = fmt.decode(params)?;   // borrows `params`, no copy
                   encode_envelope(self.inner.send(p.msg), fmt, out) }
            1 => { let p: ChatHistoryParams = fmt.decode(params)?;
                   encode_envelope(self.inner.history(p.limit), fmt, out) }
            _ => Err(RuntimeError::UnknownCall),
        }
    }
}

// 6. impl CallProtocolMeta for the marker type — calls_names() in declaration order
```

Everything here is mechanical over the `Protocol` / `Function` IR. The only
inputs a generator needs beyond what it already reads for structs are the
runtime trait names (`CallSystemConsumer`, `Dispatch`, `WireFormat`,
`RuntimeError`) — which is what this section pins down. Note the `'de` lifetime
on `Msg` and `*Params`: generated types borrow from the receive buffer rather
than owning copies (§4.6).

#### How params, results and errors are carried

There is **no runtime message object** — no `Message`, no `Parameter`, no
`Vec<arg>`. The schema is fully known at codegen time, so every call site is
statically typed and the generator emits a named struct per function instead:

| Piece | Emitted as |
|---|---|
| params | `struct <Proto><Fn>Params<'de> { … }` — one field per argument, in declaration order |
| result | the return type directly (`Ack`, a primitive, …) |
| error | `enum <Proto><Fn>Error { <Named>(<Named>), … }` — schema `!` errors only; plus a per-protocol union `<Proto>Error`. The client wraps in `CallError<E>` for infra failure (§4.4) |
| envelope | a small runtime type: `{ ok: R }` \| `{ err: { id: u16, body: &'de [u8] } }` (§4.4) |

The params struct **is** the message. It is a stack struct literal at the call
site (zero cost), serialized in one pass straight into the call system's reused
buffer, and on the receiving side decoded as a borrow into the receive buffer.

`Message` / `Parameter` (the old `setup/abstract_call.rs`) were built for a
*dynamic, runtime-assembled* argument list (`&dyn Any`) — a model Comline doesn't
need, and one that can't serialize anyway (`dyn Any` has no `Serialize`). The
whole `setup/` layer was deleted in 7d.

Cases:

- **Zero args** (`function poke();`) — no params struct; empty payload;
  `call(Kind::Id(n), &())`.
- **Many args** — one struct, or a tuple where the framing wants positional
  params (JSON-RPC arrays); field / element order is declaration order.
- **`AbstractCall<M>`** — its only content was `{ settings, parameters }`. Per-call
  settings are deferred (§4.4), so `call` takes `&P` directly and `AbstractCall`
  + `CallProtocolMeta::make_call` are dropped; a thin wrapper returns only if
  settings land. `CallProtocolMeta` keeps `calls_names()` / `call_name_from_id()`.

### 4.3 — Runtime additions this needs

Shapes chosen for the §4.6 budget — sync core, write-into-buffer, borrowed
decode. The trait-level ones landed in `comline-runtime`'s `contract` module
(rollout step 7a); the MessagePack `WireFormat` in `format` (7b); the framing +
transport + `serve` path in `wire` / `transport` / `serve` (7d); the `client`
side and a `Tcp` transport (7e). Rows below reflect what was built; only the
`Alloc` seam is still open.

| Add | Shape | For |
|---|---|---|
| `RuntimeError` | `enum { Transport, Serialization, Framing, Timeout, UnknownCall, Remote { id: u16 } }` — `core::error::Error`, **lifetime-free** (`'static`, storable) | replace `Result<T, ()>` everywhere |
| `trait Dispatch` | `fn dispatch<W: WireFormat>(&self, Kind, params: &[u8], &W, out: &mut dyn BufMut) -> Result<(), RuntimeError>` — sync; **generic over the format** (a `&dyn WireFormat` isn't object-safe — generic methods), the provider is generic over `D` anyway (no vtable) | provider call system holds `&D` and routes inbound frames to it |
| `Client::call<P>` | `fn call<P: Serialize + ?Sized>(&mut self, call_id: u16, &P) -> Result<(Envelope<'_>, &W), RuntimeError>` — frames + sends, blocks for the reply, hands back the envelope (borrowing the recv buffer) **and** the format, both out of one `&mut self`. The generated stub decodes `Ok` → `R` or maps an `Err` ordinal → `CallError<E>`. Replaces `send_async_call<M>` (the one-type-param bug). *Built (7e); one call outstanding, pipelining additive.* |
| `enum CallError<E>` | `{ App(E), Runtime(RuntimeError) }` + `From<RuntimeError>` | the one runtime type that adds infra failure to a schema-only error enum (§4.4) |
| `trait WireFormat` | `encode<T: Serialize + ?Sized>(&self, &T, &mut dyn BufMut) -> Result<(), RuntimeError>` / `decode<'de, T: Deserialize<'de>>(&self, &'de [u8]) -> Result<T, RuntimeError>` — no `Vec` return, borrow on decode. `format::MsgPack` implements it over `rmp-serde` (7b, `std`-gated). | the serialization axis; the call system is generic over one |
| `wire` framing | free fns — `encode_request` / `encode_request_header` (client frames the header then serializes params in after it) / `decode_request(&[u8]) -> Option<(u16, u64, &[u8])>` and the response pair (`request_id` + envelope). `no_std`, alloc-free, borrow on decode | one frame per message; datagram-oriented |
| `trait Transport` + `Server` / `Client` | `Transport::{send(&[u8]), recv(&mut Vec<u8>)}` — sync, frame-oriented; `InMemory` (mpsc, `duplex()`) and `Tcp` (`u32`-length-prefixed stream, `MAX_FRAME`-bounded) impls under `std`. `Server<D, W>` holds `D` + `W` + 3 reused buffers; `Client<T, W>` owns the transport + format + request-id counter + 2 reused buffers | the provider loop and the consumer call side; `alloc`-gated (`Vec` buffers) |
| wire envelope | `Envelope<'a>` — `Ok(&'a [u8])` \| `Err { id: u16, body: &'a [u8] }`, one tag byte (`0` / `1`) then `id` little-endian; `encode_ok` / `encode_err` / `decode` helpers | carry a raised error back to the client stub |
| `trait BufMut` | `put_slice` (+ `put_u8` / `put_u16_le` / `put_u64_le` defaults); `Vec<u8>` impls it under `alloc`; **`SliceBuf<'a>`** wraps a fixed `&mut [u8]` with an `overflowed` flag for the no-`alloc` tier | the receive + encode buffers, **injected once at setup** (§4.6), reset not realloc'd per call |
| `trait Alloc` | seam for owned bits — global (`alloc`) \| arena \| none; chosen once at setup. *Not built yet.* | `.to_owned()` copies and decoded collection spines |

An **`AsyncDispatch`** / async client `.call().await` layer sits behind the
`std` feature (§4.6); the generator emits it additively.

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

#### Error grouping — **decided**

**Generated types.**

- **Per-function schema-error enum** — `<Proto><Fn>Error`, one variant per `! E`
  in that function, `Variant(E)` where `E` is the generated struct from the
  `error` decl. Pure schema: no runtime types, `no_std`, reusable. A function
  with no `!` gets an empty enum (or `Infallible`).
- **Per-protocol union** — `<Proto>Error` over every `!` in the protocol, with
  `From<<Proto><Fn>Error>` for each function. Additive, for a caller that wants
  one `match` for the whole service.
- **`enum CallError<E> { App(E), Runtime(RuntimeError) }`** — the *one* runtime
  type that adds infra failure. Not generated; lives in `comline-runtime`.

**Where each lands.**

| side | signature | why |
|---|---|---|
| provider trait | `fn send(&self, …) -> Result<Ack, ChatSendError>` | schema errors only — the impl can't fabricate a `RuntimeError` |
| client stub | `fn send(&mut self, …) -> Result<Ack, CallError<ChatSendError>>` | the caller *can* hit transport / timeout / a garbage frame |
| broad client handler | `CallError<ChatError>` via `?` and the `From` impls | one `match` for the service |

**On the wire — schema-global error ordinal.** *(Built — core#47.)* The
envelope's `err` carries `{ id: u16, body: &'de [u8] }`. `id` is
`FrozenUnit::Error.ordinal` — **compiler-assigned at freeze** (`plan_error_space`
in `incremental.rs`): local `error` decls take `0..N` in declaration order, and
each foreign error a `throws` names is appended a re-export slot. `Function.throws`
is `Vec<u16>` of those ordinals. Append-only discipline (retire in place, never
reorder or reuse) is the author's to keep; version-diff *enforcement* of it is a
follow-up. `body` is the error struct's `fields`, borrowed from the receive
buffer.

- **Name-oriented framings** (JSON-RPC) put the error *name* on the wire instead;
  the generator has the ordinal↔name↔struct mapping both directions. Mirrors
  `Kind::{ Id, Named }`.
- **A `use`d cross-schema error** gets a re-export slot in the importing schema's
  ordinal space (`FrozenUnit::Error` with `imported_from: Some(ns)`, fields +
  message carried over from the source schema), so the wire `id` stays a single
  `u16`. An unresolvable `! Name` still gets a stable slot, marked
  `<unresolved: Name>`.
- **Unknown ordinal** (newer peer raised an `! E` past what the client
  generated) → `CallError::Runtime(RuntimeError::Remote { name, raw })`, borrowed
  per §4.6. Adding `! E` is a compatible change (old peers land here); removing a
  `!` reference is compatible (dead variant).

**`message` renders client-side.** `error Foo { message = "…{self.name}…" }` →
a generated `Display` / `core::error::Error` impl that does the `{self.field}`
substitution locally. Only `fields` travel; the template is baked into codegen.

**Raise-site field values** — the schema can't yet write
`! Foo(name = x)` ([guide](../guide/idl/error.md)); the generated Rust *impl*
returns a fully-built `Foo { name }`, so this language gap doesn't block codegen.

#### `synchronous` / one-way — **decided; IR changes built (core#46)**

`Function.synchronous: bool` conflated three things: whether the call has a
response (a wire fact), whether the generated API blocks or `.await`s (a binding
choice), and how the peer schedules handlers (server config). Only the first
belongs in the schema, and it is already carried by `_return`.

- **`synchronous` is removed from the IR.** *(Done.)*
- **One-way ⟺ `_return == None`.** No request id, no response frame; `! E` on
  such a function is a **compile error** (nowhere to deliver it). The generated
  caller returns `Result<(), TransportError>` — it can learn the frame didn't
  leave the box, never a remote outcome. One-way calls are inherently sync on
  the client (nothing to await) even under the async layer.
- **`KindValue` gains `Unit`** *(done)* so `-> ()` is expressible and *distinct*
  from omitting the return: `commit() -> ()` freezes as
  `_return: Some(KindValue::Unit)` and gets an empty `ok` ack; `commit();`
  freezes as `_return: None` and doesn't reply. Without it, "ack, no value"
  would force an empty `struct` per call. (Streaming, when designed, extends this
  further — `Return::{ None, One(KindValue), Stream(KindValue) }`, §4.7.)
- **Blocking vs async** is the §4.6 generator option — sync core trait always,
  `async` additive behind `std`. Not in the schema, does not travel.

**One-way means no *application* response.** TCP still gives byte-delivery;
UDP / lossy transports are best-effort.

#### Transport, framing & format — needs design

Three layers, mostly orthogonal, **none named in the schema**:

| Layer | Examples |
|---|---|
| transport | TCP, UDP, QUIC, Unix socket, WebSocket, in-process |
| framing / call system | JSON-RPC, a compact length-prefixed binary framing, gRPC-style |
| serialization (`WireFormat`, §4.3) | JSON, MessagePack, bincode, CBOR |

Per §4.6 the generated code is `serde`-only and codec-agnostic, so there is
nothing format-specific to generate — nothing to forward-declare.

**The schema declares *requirements*, not mechanisms.** In the congregation (a
config `FrozenUnit`, like `CodeGeneration`), or a schema `settings` block
([guide](../guide/idl/settings.md)):

- **`reliable`** — no silent message loss
- **`ordered`** — per-connection ordering (a stateful protocol, `open()` before
  `write()`, needs this)
- **`duplex`** — the peer can push (needed once streaming exists)
- **`max_message_bytes`**
- **delivery ack for one-way calls** — default fire-and-forget; an API where a
  lost notification is unacceptable declares it required, and the generated
  `notify(...) -> Result<(), TransportError>` then also fails on no ack in a
  window (still no *value*, just confirmed receipt)

A one-way-only API can **waive** `reliable` / `ordered` — that is what makes it
legal over UDP.

**The runtime picks the concrete stack and checks it.** Transport + framing +
`WireFormat` are chosen at `.serving()` / `.connect()` (like §4.6's memory
config). Setup **verifies the composed stack meets the declared requirements** —
compile-time via generator options where it can, runtime assert otherwise
(`reliable + ordered` → TCP / QUIC-stream / Unix / in-process qualify; raw UDP
does not).

**A connection handshake — built ([runtime#8](https://github.com/ComlineProject/runtime/pull/8) + [comline-rust#6](https://github.com/ComlineProject/comline-rust/pull/6)).** Each end sends `Handshake { ir_hash, wire_format, framing, capabilities }` as the first frame and `check`s the peer's — refuses (`RuntimeError::Handshake`) on an `ir_hash` / `wire_format` / `framing` mismatch (capability bits may differ). Catches "one end msgpack, the other JSON", which no-declaration otherwise leaves as garbage at runtime.

- `wire_format` / `framing` are carried as an **FNV-1a `name_hash` of a name**, not a numeric id — `WireFormat::name()` (`"msgpack"`), a user add-on picks a namespaced name; no central id registry. `Handshake` stays fixed-size (31 bytes) and `Copy`.
- **Two modes.** `Client::connect` / `Server::serve_handshaked` (checked) vs `Client::new` / `Server::serve` (**skip it — "misaligned mode"**, documented, for a legacy peer / no back-channel / an embedded target that can't spend the round trip). The generator emits `<Proto>Client::connect` and `<Proto>Dispatcher::serve` for the checked path, filling the `Handshake` from a generated `IR_HASH` const.
- Still open: a `WarnOnly` middle mode (exchange, log, proceed) for migrations; a canonical cross-language `ir_hash` from `core`'s CAS (today it's FNV over the generator's frozen-unit `Debug` view, threaded per-generator).

The schema's transport requirements still constrain *your* stack selection at setup; nothing cross-checks that the peer honours them.

**Datagram vs stream is the one real structural fork.** Stream (TCP,
QUIC-stream, Unix) → framing length-prefixes for message boundaries. Datagram
(UDP, QUIC-datagram) → one message per datagram, size-bounded; request/response
then needs the framing to own correlation + retransmit + dedup, or to restrict
to one-way. A framing declares stream-vs-datagram, a transport declares what it
provides, setup checks compat. QUIC's stream *and* datagram multiplexing is a
later opportunity, not now.

**In-order processing.** Default: in-order on one connection with the §4.6 sync
dispatcher. The `std` `AsyncDispatch` layer may start / complete handlers out of
order; a stateful protocol declares `ordered`, a throughput-oriented one opts
into concurrent.

Optionally, a `default_wire = "msgpack"` hint in the package — advisory, for
tooling and `comline new`, not a constraint.

This wants its own design pass before `comline-rust`, and it adds a config
`FrozenUnit` on the §2 side.

#### Per-call settings — **decided**

**IR.** `FrozenUnit::Function` gains `parameters: Vec<FrozenUnit>` (like
`Struct` / `Protocol`) holding `@key=value` function annotations as
`Property { name, expression }`. Open namespace — the runtime documents and
validates the keys it acts on and ignores the rest (forward-compat, same as the
generator `options` map in [Generation](generation.md#language-version-dialect)).

**v1 knob set — two:**

| annotation | meaning | travels? |
|---|---|---|
| `@timeout_ms = N` | how long the client waits for the response; request/response only | no — local wait |
| `@idempotent` | marker: calling twice is safe. **No behavior yet** — the gate a future `retry` will require | no — advisory metadata |

`priority` / `deadline` (would travel) / `retry` / `compression` are named as
*later*, each with its wire implication noted when it lands.

**`idempotent` is a function property, not a call option** — it's fixed per
function, baked into generated metadata (e.g. `CallProtocolMeta::is_idempotent(id)`),
never in `CallOptions`.

**`timeout` resolves through three levels**, call-site wins:

1. `@timeout_ms` — the schema's default.
2. consumer `comline.toml` — override for a whole dependency
   (`[calls."pkg::chat"] timeout_ms = 5000`).
3. call-site — `client.with_options(CallOptions { timeout: Some(d) }).send(msg)`.
   `.with_options(…)` returns a lightweight view with the **same method set**, so
   the bare `client.send(msg)?` (§4.6) is untouched and no `_with` variant
   doubles the method count.

Falls back to a runtime global default if none is set. **Nothing travels in
v1**; when `deadline` / `priority` land they go in the frame and the handshake
advertises support.

### 4.6 — `no_std`, memory, and the performance budget

**Decided:** `no_std`-first (one crate, `alloc` / `std` additive); borrowed
generated types by default with `.to_owned()` as the escape; **memory is
configured once at setup, never threaded through a call**; the hardening
measures below. Open: the arena `Alloc` mode ships after the global-default one.

#### The user-facing rule

> Set memory up at the start *if you want to*. After that, calls and handlers
> are plain — no buffer, no allocator, no lifetime past the borrow.

```rust
// configure once — or skip it entirely under the `alloc` feature, where
// `Server::new` just grows a `Vec<u8>` for each reused buffer.
let mut server = Server::new(ChatDispatcher(MyChat), MsgPack);
    // .with_buffers(recv, envelope, response)  // no-alloc: three &mut [u8; N]
    // .with_arena(&mut region)                 // opt-in: bump region, reset per call
server.serve(&mut transport)?;    // transport: any `Transport` impl

// every call site, forever:
impl Chat for MyChat {
    fn send(&self, msg: Msg<'_>) -> Result<Ack, ChatSendError> { /* … */ }
}
client.send(msg)?;                 // no buffer, no allocator in the signature
```

The only ambient complexity at a call site is the `'_` on borrowed args — the
deliberate cost of borrowed-by-default (§4.2), and what makes "wipe after use"
actually work.

#### The budget

One call, transport already connected, is designed to cost:

| | |
|---|---|
| header | one `u16` call id + one `u64` request id written into a reused buffer |
| encode | one serialize pass of the params struct straight into that buffer — no intermediate `Message`, no `Vec` |
| send | one transport write |
| receive | one transport read into a reused buffer |
| decode | one **borrowed** deserialize — `R` / `*Params` point into the read buffer |
| dispatch | one index into a jump table (`match idx { 0 => … }`), no hashing, no string compare |
| **allocations** | **zero** on the happy path |

Anything that breaks "zero allocations on the happy path" has to justify itself.
The error path may allocate.

7e's `Client::call` and `Server::serve_one` already hold to this — request-id
counter aside, they only `clear()` and refill buffers they own. Still to close:
the dispatcher needs a reusable scratch for the reply body before it becomes an
`Envelope` (the per-arm `Vec` in the hand-written test dispatchers) — either a
buffer `serve` hands down or one the generated dispatcher owns.

#### Memory

- **Buffers are injected once, at setup.** After `.serving(…)` / `.connect(…)`
  the call system owns the receive and encode buffers and reuses them —
  `clear()` / reset per call, never realloc'd. Default under `alloc`: a growable
  `Vec<u8>`. Under no-`alloc`: the caller passes `&mut [u8; N]` and an over-long
  frame is a `RuntimeError`, not a panic.
- **An `Alloc` mode, also chosen once at setup**, for the *owned bits* —
  `.to_owned()` copies and the spine of a decoded `Vec<T>` / `BTreeMap` (the
  elements borrow; the container can't, unless the wire format is already laid
  out as `&'de [T]`):

  | mode | what it is | for |
  |---|---|---|
  | **global** — default, `alloc` feature | the registered `#[global_allocator]` | you don't want to think about it |
  | **arena** — opt-in | a caller-supplied bump region, reset (not freed) per call; doubles as the zeroization unit | embedded, throughput, hardening |
  | **none** — no-`alloc` | — | the generator then rejects schemas whose types need heap, or forces those fields to `&'de` |

  `Vec` / `String` / `Box` are `alloc`, **not `std`** — they work in `no_std`
  with a `#[global_allocator]`. The strict tier is `no_std` *and* no `alloc`.
  Rust's per-container allocator API (`Vec::new_in`, `Allocator`) is still
  nightly, so the arena is its own seam, not `alloc::Vec` with a custom `A`.
- Ship the **global-default** first; the arena is a follow-on on the same seam.

#### Hardening (decided, independent of the above)

- **Bounded decode.** `WireFormat` decoders enforce a max frame size, max
  collection length and max nesting depth; a hostile length prefix is rejected
  *before* any allocation.
- **Buffer zeroization.** The receive + encode buffers (and the arena, if used)
  are `zeroize`d after each call, behind a `hardening` feature that is **on by
  default**.
- **No `unsafe`.** `#![forbid(unsafe_code)]` in generated code and in the decode
  path.

#### Sync core `Dispatch`

`async fn` in a `dyn` trait forces a boxed future per call, so the core
`Dispatch` is **sync** and the generated provider trait is **sync by default**;
the provider is generic over `D: Dispatch` (static dispatch, no vtable, no box).
Async server concurrency is an `AsyncDispatch` + executor layer behind the `std`
feature — emitted additively, never on the `no_std` path.

#### `no_std` layering

The repo decision folds `core_no-std` into a `std` feature on one crate:

| Tier | Has | Contents |
|---|---|---|
| **core** (`no_std`, no `alloc`) | — | `contract/` — `Dispatch`, `WireFormat`, `RuntimeError`, `Kind`, `BufMut` + `SliceBuf`, `Envelope`, `CallError` — plus `wire` framing. Pure `(&[u8], id) -> Result<(), _>` transforms over injected buffers. *(Built: 7a + 7d.)* |
| **`alloc`** feature | `alloc` | `serve::Server`, `client::Client`, the `transport::Transport` trait, owned generated types, the `Alloc` seam. *(Built: 7d–7e; `Alloc` open.)* |
| **`std`** feature | `std` | `format::MsgPack`, `transport::{InMemory, Tcp}`, `package_abi`; later — `AsyncDispatch` + executor, blocking wrappers. *(Built: 7b MsgPack, 7d InMemory, 7e Tcp.)* |

**Transport is not in the `no_std` core** — an embedded target hands the runtime
bytes in and takes bytes out itself. The `no_std` runtime *is* framing + dispatch
+ (de)serialization over borrowed, injected buffers. Generated code
(`comline-rust` output) targets the core traits and is `#![no_std]` +
`extern crate alloc` by default; `std` conveniences are additive.

### 4.7 — Still open beyond the above

- **The per-language-runtime ↔ core-runtime seam.** The
  [runtime guide](../guide/runtime/index.md) says each language has a "thin
  runtime that speaks to the core runtime" — that trait boundary is nowhere yet.
  For Rust it's degenerate (the target repo *is* Rust); it becomes real with the
  second `lib`-mode language, and it has to respect the §4.6 budget across the
  FFI edge (surface 5) too.
- **Streaming / server-push.** `Event<Incoming, Outgoing>` and the `watch`
  plumbing hint at it; no design. A `function` returning a stream has no IR
  representation.

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
rollout step 4). Surface 4's design decisions are **all made** (§4.4 + §4.6);
what remains is below the decision line:

- **§4.4** — the design is settled, the `WireFormat` / `Transport` / framing
  trait signatures are built (7b–7e), and the IR changes the decisions imply are
  landed (`Function.parameters`, `KindValue::Unit`, drop `synchronous` — core#46;
  `throws: Vec<u16>` + error ordinals — core#47). The connection handshake
  (runtime#8 + comline-rust#6), pluggable framing incl. JSON-RPC (runtime#10 +
  comline-rust#8), the per-`protocol` `@framing` selector on the generated
  `connect` / `serve` helpers (comline-rust#9), and its `comline.toml`
  package-wide `default_framing` (generation#17 + comline-rust#10 + cli#27) are
  built. Still open at the wire level: a `WarnOnly` handshake mode,
  multi-`throws` (`! A, B`) grammar, version-diff enforcement of the ordinal
  append-only rule, and the transport-requirements config unit.
- **§4.6** — decided; the buffer-reuse budget is met by 7d–7e (`Client` /
  `Server`), the dispatcher's reply-body scratch and the arena `Alloc` mode are
  the follow-ons.
- **§4.7** — the per-language-runtime seam, streaming — deliberately later.
- **§5** — the FFI ABI, parked with G2c.

Smaller, outside surface 4: float primitives are commented out in `core`
(surface 1); whether the schema IR gets an explicit `FrozenUnit::IrVersion`
(Versioning, above).
