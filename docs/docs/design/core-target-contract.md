# The `core` ↔ target contract

Status: **draft** — surfaces 1–3 (schema IR, config IR, codegen contract) are
solid and ready to build a `code` generator on; surface 4 (runtime API +
generated protocol) has a worked design in §4 — `no_std`-first, borrowed
generated types, memory configured once at setup, a zero-alloc call budget and a
hardening baseline (§4.6), call addressing, error grouping and `synchronous` /
one-way (§4.4) decided; the `WireFormat` axis, runtime behavior contracts and
per-call settings (§4.4) still open · Affects
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
  `Option<KindValue>` (`None` ⟹ one-way, §4.4). Slated: drop `synchronous`;
  `throws` becomes `Vec<u16>` (schema-global error ordinals) at freeze (§4.4)
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
    fn dispatch(&self, call: Kind, params: &[u8], fmt: &dyn WireFormat, out: &mut dyn BufMut)
        -> Result<(), RuntimeError>
    {
        match call.index(Chat::CALLS)? {                          // index-based jump table
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

`Message` / `Parameter` (`setup/abstract_call.rs`) were built for a *dynamic,
runtime-assembled* argument list (`&dyn Any`) — a model Comline doesn't need, and
one that can't serialize anyway (`dyn Any` has no `Serialize`). They are deleted.

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

Shapes chosen for the §4.6 budget — sync core, write-into-buffer, borrowed decode:

| Add | Shape | For |
|---|---|---|
| `RuntimeError` | `enum { Transport, Serialization, Framing, Timeout, UnknownCall, Remote { name, raw } }` — `core::error::Error`, no `String` on the happy path | replace `Result<T, ()>` everywhere |
| `trait Dispatch` | `fn dispatch(&self, Kind, params: &[u8], &dyn WireFormat, out: &mut dyn BufMut) -> Result<(), RuntimeError>` — sync, no return alloc | provider call system holds `&D` / `Arc<D>` (generic, not `dyn`) and routes inbound frames to it |
| `CallSystemConsumer::call<'de, P, R, E>` | `fn call<P: Serialize, R: Deserialize<'de>, E>(&'de mut self, Kind, &P) -> Result<R, CallError<E>>` — `R` / `E` borrow the response buffer | replaces `send_async_call<M>` (the one-type-param bug) |
| `enum CallError<E>` | `{ App(E), Runtime(RuntimeError) }` | the one runtime type that adds infra failure to a schema-only error enum (§4.4) |
| `trait WireFormat` | `encode<T: Serialize>(&self, &T, out: &mut dyn BufMut)` / `decode<'de, T: Deserialize<'de>>(&self, &'de [u8]) -> Result<T, _>` — no `Vec` return, borrow on decode | the serialization axis; call systems are generic over / configured with one |
| wire envelope | tag byte + `ok: R` \| `err { id: u16, body: &'de [u8] }` — schema-global error ordinal + the error's fields, both borrowed (§4.4) | carry a raised error back to the client stub |
| `trait BufMut` | minimal `no_std` append target (`put_slice`, `put_u8`, …); `Vec<u8>` and `&mut [u8]` implement it | the receive + encode buffers, **injected once at setup** (§4.6), reset not realloc'd per call |
| `trait Alloc` | seam for owned bits — global (`alloc`) \| arena \| none; chosen once at setup | `.to_owned()` copies and decoded collection spines |

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

**On the wire — schema-global error ordinal.** The envelope's `err` carries
`{ id: u16, body: &'de [u8] }`. `id` is the error's position in the schema's
frozen `Error`-unit sequence — **compiler-assigned, frozen into the IR,
version-diff enforced** (an `error` decl is retired in place, never deleted or
reordered; its ordinal is never reused). `throws` in the IR shifts from
`Vec<String>` to `Vec<u16>` (names resolved at freeze) so the ordinal is itself
version-checked. `body` is the error struct's `fields`, borrowed from the
receive buffer.

- **Name-oriented framings** (JSON-RPC) put the error *name* on the wire instead;
  the generator has the ordinal↔name↔struct mapping both directions. Mirrors
  `Kind::{ Id, Named }`.
- **A `use`d cross-schema error** gets a re-export slot in the importing schema's
  ordinal space, so the wire `id` stays a single `u16`.
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

#### `synchronous` / one-way — **decided**

`Function.synchronous: bool` conflated three things: whether the call has a
response (a wire fact), whether the generated API blocks or `.await`s (a binding
choice), and how the peer schedules handlers (server config). Only the first
belongs in the schema, and it is already carried by `_return`.

- **`synchronous` is removed from the IR.**
- **One-way ⟺ `_return == None`.** No request id, no response frame; `! E` on
  such a function is a **compile error** (nowhere to deliver it). The generated
  caller returns `Result<(), TransportError>` — it can learn the frame didn't
  leave the box, never a remote outcome. One-way calls are inherently sync on
  the client (nothing to await) even under the async layer.
- **`KindValue` gains `Unit`** so `-> ()` is expressible and *distinct* from
  omitting the return: `commit() -> ()` gets an empty `ok` ack; `log(msg)`
  doesn't reply. Without it, "ack, no value" would force an empty `struct` per
  call. (Streaming, when designed, extends this further —
  `Return::{ None, One(KindValue), Stream(KindValue) }`, §4.7.)
- **Blocking vs async** is the §4.6 generator option — sync core trait always,
  `async` additive behind `std`. Not in the schema, does not travel.

**One-way means no *application* response.** TCP still gives byte-delivery;
UDP / lossy transports are best-effort.

#### Runtime behavior contracts — needs design

Two guarantees a project may need to rely on or tune, neither of which is a
per-function schema property:

- **Delivery ack for one-way calls.** Default: fire-and-forget. A deployment can
  turn on a minimal ack frame for one-way calls (setup knob, like §4.6's memory
  config) so `notify(...) -> Result<(), TransportError>` also fails on no ack in
  a window — still no *value*, just confirmed receipt. An API where a lost
  notification is unacceptable can **declare this as a requirement** so the
  generated client / setup enforces it.
- **In-order processing.** Default: in-order on one connection with the §4.6 sync
  dispatcher. The `std` `AsyncDispatch` layer may start / complete handlers out
  of order. A stateful protocol (`open()` before `write()`) can **declare it
  needs in-order handling**; a throughput-oriented one can opt into concurrent.

Both fit the same shape: a **default**, a **runtime-setup knob**, and a
**project-declared requirement** (in the congregation, or a schema `settings`
block — [guide](../guide/idl/settings.md)) that makes the generated code assert
the chosen runtime can provide it. This overlaps **per-call settings** (below)
and the config IR (§2); it wants its own design pass before `comline-rust`.

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

### 4.6 — `no_std`, memory, and the performance budget

**Decided:** `no_std`-first (one crate, `alloc` / `std` additive); borrowed
generated types by default with `.to_owned()` as the escape; **memory is
configured once at setup, never threaded through a call**; the hardening
measures below. Open: the arena `Alloc` mode ships after the global-default one.

#### The user-facing rule

> Set memory up at the start *if you want to*. After that, calls and handlers
> are plain — no buffer, no allocator, no lifetime past the borrow.

```rust
// configure once — or skip it entirely under the `alloc` feature
let service = ProviderSetup::with_transporter(tcp)
    .with_call_system(JsonRPCv2::new)
    // .with_buffers(recv, send)   // default: growable Vec<u8> (alloc); required &mut [u8; N] under no-alloc
    // .with_arena(&mut region)    // opt-in: bump region, reset per call
    .serving(MyChat);

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
| **core** (`no_std`, no `alloc`) | — | `CallProtocolMeta`, `Dispatch`, `WireFormat`, `RuntimeError`, `Kind`, `BufMut`, the envelope, the `Alloc` seam. Pure `(&[u8], id) -> Result<(), _>` transforms over injected buffers. |
| **`alloc`** feature | `alloc` | the global `Alloc` mode, owned generated types, `Vec`-returning `WireFormat` impls |
| **`std`** feature | `std` | tokio transport, TCP, the `Arc<RwLock>` setup builders, the `watch`-channel events, `AsyncDispatch`, blocking wrappers |

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
rollout step 4). The live design work is all in **surface 4**:

- §4.4 — the `WireFormat` axis, runtime behavior contracts (delivery ack,
  in-order processing), per-call settings — each needs a decision before
  `comline-rust`, step 5. Call addressing, error grouping and `synchronous` /
  one-way are decided.
- §4.6 — decided (`no_std`-first, borrowed-default, memory-set-up-once, the
  hardening trio); the runtime doesn't implement it yet, and the arena `Alloc`
  mode is a follow-on after the global default.
- §4.7 — the per-language-runtime seam, streaming.
- §5 — the FFI ABI, parked with G2c.

Smaller, outside surface 4: float primitives are commented out in `core`
(surface 1); whether the schema IR gets an explicit `FrozenUnit::IrVersion`
(Versioning, above).
