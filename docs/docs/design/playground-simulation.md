# Playground simulation — Phase 1

Status: **built** — Phase 1 spec for the ["simulate machines"](playground-and-tutorial.md#the-runtime-demo)
runtime demo. **1a** is done
([playground#15](https://github.com/ComlineProject/playground/pull/15)):
`describe_project` turns the frozen IR into the protocol description below, its
`ir_hash` verified to equal what the generators emit. **1b** is done
([playground#16](https://github.com/ComlineProject/playground/pull/16)): the
runtime is vendored, `TappedTransport` + `GenericClient` / `GenericDispatch` are
in, and the drift guard — route B's frames byte-for-byte against the generated
`ChatDispatcher`'s — passes in CI. **1c** is done
([playground#17](https://github.com/ComlineProject/playground/pull/17)): the six
behaviours, the `Session` model, and `engine.connect` — the sim runs end to end
from a script. **1d** is done
([playground#18](https://github.com/ComlineProject/playground/pull/18)): the
full-width simulate view — palette, canvas + SVG wire, inspector with per-function
behaviour pickers, the IR-driven call form — driven through a real DOM
(`linkedom`) in CI. **1e** is done
([playground#19](https://github.com/ComlineProject/playground/pull/19)): the
expandable frame inspector (decoded envelope, hex, framing, Δ latency) and the
handshake-refusal path — edit a schema, resync one end, watch the connection be
refused. **Phase 1 is complete.** Buildable because `@comline/runtime` already
ships the pieces the wire needs: `duplex()` for a
connected in-memory `Transport` pair, `Client.connect` / `Server.serveHandshaked`
that run the real handshake and refuse on an `IR_HASH` mismatch, `Reply` with
`ok` / `err` / `none` outcomes, and both framings. Nothing here needs a
`comline-core` change beyond one read-only WASM function. Two shape decisions are settled: the simulation is a
**full-width view** (the canvas, inspector and frame log do not fit the existing
right pane), and `@comline/runtime` is **vendored** into the app (it is an
unpublished workspace package, and this matches how the WASM crate pins
`comline-core` by git rev). The build follows **route B** — drive the frozen IR
through the real runtime, no code generation or transpilation on the path ·
Affects `ComlineProject/playground`, later `ComlineProject/docs` (the tutorial
embeds it)

## Goal

Phase 1 makes the playground demonstrate the sentence at the heart of Comline:
two services generated from the same schema can talk, and refuse to when they
were not.

In scope:

- a **simulate view** reached from the header, reading the schemas open in the
  editor;
- a **canvas** with draggable instances and **one connection** between a client
  and a server instance;
- a **call form** generated from the chosen function's arguments, with a
  raw-JSON escape hatch;
- a fixed set of **canned server behaviours** — no user code yet;
- a **frame inspector**: every handshake / `Call` / `Reply` / `CallError` frame,
  decoded body, raw bytes, framing, direction, simulated latency.

Not in scope — see [Deferred](#deferred-to-phase-2): more than one connection,
fan-out, node-to-node forwarding; user-written behaviour code and its sandbox;
fault injection as first-class controls, time-step control, record & replay,
shareable sessions; running the actual generated module (route A).

## Vocabulary

| Term | Meaning |
|---|---|
| **Instance** | one endpoint: a protocol + a role (`server` / `client`) + its config. What the tutorial calls a "service". Not a `FrozenUnit`. |
| **Node** | a box on the canvas hosting one instance. Phase 1: node ≡ instance. |
| **Connection** | a wire between a client instance and a server instance of the same protocol — a `duplex()` pair. |
| **Behaviour** | what a server instance does for one function when dispatched; a canned function returning an outcome (`ok` / `err` / `none`). |
| **Frame** | one `Uint8Array` across the wire — a handshake frame, or a request / response frame from the framing. |
| **Tap** | a transport wrapper that records every frame and emits it to the inspector. |
| **Session** | the whole sim state — instances, the connection, behaviours, the frame log. One object, rebuilt when the schemas change. |

## Architecture

TypeScript in the app, on the main thread. The WASM module gains exactly one new
read-only function ([`describe_project`](#the-wasm-addition-describe_project));
the wire, the client/dispatch glue, the behaviours and the UI are app code over
`@comline/runtime`.

```text
WASM.describe_project() ──▶ Session (instances, behaviours, connection)
                                    │
                                    ▼  engine
                    ┌───────────── connection ─────────────┐
                    │  GenericClient      GenericDispatch   │
                    │        └── TappedTransport ×2 ──┘     │   duplex()
                    └──────────────────┬───────────────────┘
                                       ▼
                                   Frame log   (every frame, copied)
```

One direction of dependency: the IR describes the shape, the engine wires the
runtime, the tap observes. Nothing downstream feeds back into the compiler.

Module layout:

```text
app/src/sim/
  shape.ts       TS mirror of describe_project's output + type helpers
  runtime/       vendored @comline/runtime src (8 files, zero deps, MPL-2.0)
  transport.ts   TappedTransport over a duplex() end; Frame events
  generic.ts     GenericClient, GenericDispatch — route B, IR-driven
  behavior.ts    the canned behaviour set + registry
  model.ts       Instance, Connection, Session
  engine.ts      build duplex, run the server loop, route client sends
  ui/
    canvas.ts    nodes + the one edge, drag
    inspector.ts per-instance config, per-function behaviour picker
    argsform.ts  IR-driven arg form + raw-JSON fallback
    framelog.ts  the frame inspector
  index.ts       mounts the simulate view, owns the Session
```

!!! note "Why vendor the runtime"
    `@comline/runtime` is an unpublished workspace package (`version 0.0.0`).
    Copy its `src/*.ts` into `sim/runtime/`, the same way the WASM crate pins
    `comline-core` by git rev. Record the source commit in a header comment;
    re-vendor when the contract moves.

## The WASM addition: `describe_project`

A pure read over the frozen units `interpret_project` already produces — no new
`comline-core` surface. It turns each compiled schema into a machine-readable
protocol description the simulator drives.

```rust
#[wasm_bindgen]
pub fn describe_project(files: JsValue) -> JsValue; // -> ProjectShape

struct ProjectShape { schemas: Vec<SchemaShape> }

struct SchemaShape {
    namespace: String,                 // "chat"
    ir_hash:   String,                 // "0x{:016x}" of schema_ir_hash(&units)
    protocols: Vec<ProtocolShape>,
    errors:    Vec<ErrorShape>,        // { ordinal, name, message, fields }
    types:     Vec<TypeDef>,           // every Struct / Enum, for the args form
}

struct ProtocolShape {
    name:      String,
    framing:   String,                 // "datagram" | "jsonrpc"
    functions: Vec<FnShape>,
}

struct FnShape {
    name:    String,
    index:   u32,                      // 0-based declaration order = the Call id
    oneway:  bool,                     // _return is None
    args:    Vec<ArgShape>,            // { name, ty: TypeRef }
    returns: Option<TypeRef>,
    throws:  Vec<ThrowShape>,          // { ordinal, name } joined to errors[]
}

// TypeRef =
//   { kind: "prim",  name: "u64" }
// | { kind: "ref",   name: "Message" }
// | { kind: "array", of: TypeRef }
// | { kind: "unit" }
// | { kind: "union", of: [TypeRef] }
```

Mapping rules:

- **index** — a function's position in its `Protocol.functions`; what
  `resolveKind` matches on the wire (the generated `CHAT_CALLS` array is the same
  order).
- **framing** — from a `Property { name: "framing" }` in the protocol's
  `parameters`; else the package `default_framing`; else `"datagram"`.
  `"jsonrpc"` → `JsonRpcFraming` (`name "jsonrpc-2.0"`), anything else →
  `DatagramFraming` (`name "comline.datagram"`).
- **oneway** — `_return.is_none()`. Distinct from `Some(Unit)`, which still sends
  an empty `ok` reply.
- **throws** — each `u16` ordinal joined to the matching `FrozenUnit::Error` by
  `ordinal`; an unresolved slot keeps its number with `name: "<unresolved>"`.
- **TypeRef from KindValue** — a frozen signature type is `Unit` → `{ unit }`,
  `Union(v)` → `{ union, of: map(v) }`, `Primitive(p)` → `{ prim, p.name() }`
  (rare — only literal defaults), or `Namespaced(n, _)`. For a `Namespaced`
  string: an `[]` suffix → `{ array, of: <rest> }`; a name declared as a
  struct/enum anywhere in the project → `{ ref, n }`; anything else → `{ prim, n }`.
  The only decision is "a type this project declares" (render its fields) vs.
  "anything else" (one scalar input) — the grammar reserves the primitive
  keywords, so a declared name can't collide with `u64` / `string` / …, which
  makes the IR-built name set the single source of truth (no primitive-name list
  to sync with `comline-core`).
- **ir_hash** — `comline_core::schema::ir::frozen::schema_ir_hash(units)` over
  the same `Vec<FrozenUnit>` (leading `Namespace` unit included) the generator
  hashes. This is the **exact call** `comline-codegen-rust` and
  `comline-codegen-typescript` make; identical by construction — a Node check
  against the built wasm confirms `describe_project`'s value equals the emitted
  `IR_HASH` for the same schema.

!!! note "Array types — confirmed"
    Frozen function args / returns / fields go through `build_kind_value(_, None)`:
    a `Type::Array` lands as `KindValue::Namespaced("T[]", None)` (the `[]` is
    appended by `type_to_string`). `TypeRef` peels the suffix; nested arrays
    recurse.

## Runtime & wire (route B)

`@comline/runtime` already ships everything: `duplex()` for a connected
in-memory `Transport` pair, `Client.connect` / `Server.serveHandshaked` which
run the real handshake and refuse on an `IR_HASH` mismatch, `Reply` with `ok` /
`err` / `none` outcomes, and the two framings.

**`TappedTransport`** wraps one `duplex()` end. `send` / `recv` pass through;
each frame is timestamped, tagged with a direction and the endpoint pair, and
emitted. Phase 1 adds one knob — a fixed `latencyMs` before delivery — so
replies do not land in the same microtask and the log reads in order. (Drop /
reorder / corrupt are Phase 3.)

**Generic client & dispatch** reproduce what the generated `ChatClient` /
`ChatDispatcher` do, reading a `ProtocolShape` instead of being emitted per
schema:

```ts
class GenericClient {
  constructor(private client: Client, private proto: ProtocolShape) {}

  async call(fnName: string, params: unknown): Promise<unknown> {
    const fn = this.proto.functions.find((f) => f.name === fnName)!;
    if (fn.oneway) return this.client.notify({ id: fn.index, name: fn.name }, params);
    const env = await this.client.call({ id: fn.index, name: fn.name }, params);
    if ("ok" in env) return this.client.codec.decode(env.ok);
    const thrown = fn.throws.find((t) => t.ordinal === env.err.id);
    throw new SimRemoteError(env.err.id, thrown?.name, this.client.codec.decode(env.err.body));
  }
}

class GenericDispatch implements Dispatch {
  constructor(private proto: ProtocolShape, private behaviors: BehaviorMap) {}
  calls() { return this.proto.functions.map((f) => f.name); }

  async dispatch(call: Kind, params: Uint8Array, codec: Codec, reply: Reply) {
    const fn = this.proto.functions[resolveKind(call, this.calls())!];
    const outcome = await this.behaviors[fn.name].run({
      params: codec.decode(params), fn, proto: this.proto,
    });
    if (outcome.kind === "ok")  reply.ok(codec.encode(outcome.value ?? null));
    if (outcome.kind === "err") reply.err(outcome.ordinal, codec.encode(outcome.data));
    // "none" — one-way, nothing sent
  }
}
```

Framing and codec come from the `ProtocolShape`: `new JsonCodec()`, and
`JsonRpcFraming` or `DatagramFraming` per `proto.framing`. The `Handshake` is
built with the schema's `ir_hash`, the codec name and the framing name — exactly
as `serveChat` does.

!!! note "Drift guard"
    Route B is a second implementation of the generator's glue. A conformance
    test runs one `send` call through `GenericDispatch` and through the committed
    `runtime/test/generated/chat.ts` fixture and asserts byte-identical frames.
    Keep it in milestone 1b and CI.

## Behaviours

Six canned behaviours. Each is `(ctx) => Promise<Outcome>` where `Outcome` is
`{ kind:"ok", value } | { kind:"err", ordinal, data } | { kind:"none" }`.
Assigned per `(instance, function)` and stored in the session.

| Behaviour | Config | Does |
|---|---|---|
| **Reply with value** | a JSON value matching the return type (seeded with its zero value) | returns it verbatim. Default for a new server instance. |
| **Echo params** | — | returns the decoded params unchanged. |
| **Increment field** | a numeric field path in the return + a base value | returns the base with that field bumped once per call. |
| **Delay then reply** | ms + a JSON value | waits, then replies. Shows a request in flight. |
| **Raise error** | one of the function's `throws[]` + that error's field values | `reply.err(ordinal, …)`. |
| **Drop** | — | never replies. The client's `call` stays pending; the request row stays open. |

A one-way function only accepts **Drop** or a no-value **Reply with value** — its
outcome is `none` regardless.

## The simulate view

A header control switches `<main>` between **edit** and **simulate**. Simulate
takes the full width. It reads the same `project()` snapshot the editor
compiles; changing a schema and returning rebuilds the `Session` (instances
keyed by protocol name survive; a vanished protocol drops its instance).

```text
┌ header   Comline Playground        [ edit  simulate ]              ok ┐
├───────────────┬─────────────────────────────────┬────────────────────┤
│ palette       │            canvas               │ inspector          │
│               │                                 │ instance  chat-1   │
│ Chat          │     ┌───────┐        ┌───────┐   │ protocol  Chat     │
│  ▪ server     │     │chat-1 │━━━━━━━━│chat-2 │   │ role      server   │
│  ▪ client     │     └───────┘  conn  └───────┘   │ framing   datagram │
│               │                                 │ ir_hash   0x6b34…  │
│ (drag onto    │                                 │ ── functions ──    │
│  the canvas)  │                                 │ send   [Reply    ▾]│
│               │                                 │ note   [Drop     ▾]│
├───────────────┴─────────────────────────────────┼────────────────────┤
│ frames                                          │ ── call ──         │
│ ▸ 001  chat-1 → chat-2  Handshake       31 B    │ as        chat-2   │
│ ▸ 002  chat-2 → chat-1  Handshake       31 B    │ fn        send   ▾ │
│ ▾ 003  chat-2 → chat-1  Call  send  #0  +8 ms   │ text      [______] │
│     datagram · 41 B · { "text": "hi" }          │ [ send ]           │
│ ▾ 004  chat-1 → chat-2  Reply send  ok          │                   │
│     { "body": "HI", "seq": 1 }                  │                   │
└─────────────────────────────────────────────────┴────────────────────┘
```

**Canvas** — hand-rolled SVG + DOM, no graph library. Drag a palette entry
(protocol × role) onto the canvas → a node; drag nodes to reposition (positions
live in the session). Drag from one node's port to another of the *same
protocol, opposite role* → the connection; Phase 1 keeps **one** (a second
replaces it). Selecting a node fills the inspector; selecting the client node
also shows the call form.

**Inspector** — instance facts (protocol, role, resolved framing, `ir_hash`);
per-function behaviour pickers (server only), expanding to that behaviour's
config built from the return type / `throws[]`; the call form (client only) — a
function picker, then an arg form from `FnShape.args`, `send` runs the call and
appends to the frame log. Errors surface inline as `ErrorName { …fields }`.

**Arg form** (`argsform.ts`) — `prim` → typed input (number / checkbox / text);
`ref` → a fieldset recursing into that struct's fields, enums as a select;
`array` / `union` / unresolved → a monospace **raw JSON** textarea parsed on
`send`. A "raw JSON" toggle on the whole form swaps every field for one textarea
of the full params object — the always-available escape hatch.

**Frame log** (`framelog.ts`) — one row per frame in delivery order: `seq`,
`from → to`, kind, function, call id `#n`, error ordinal for `CallError`,
simulated latency, byte length. Expandable: decoded body (pretty JSON), a
raw-bytes hex toggle, the framing that produced it. Handshake frames are their
own kind; a mismatch row is styled danger and reads
`connection refused · handshake`. "Clear" resets the log; the connection stays
up.

## Interaction flows

**Wire two instances and call**

1. Open **simulate**. The palette lists every protocol in the open schemas.
2. Drag `Chat · server` → `chat-1`. Drag `Chat · client` → `chat-2`.
3. Drag `chat-2`'s port to `chat-1` → a connection. The engine builds a
   `duplex()`, wraps both ends in taps, starts `chat-1`'s serve loop, runs the
   handshake. Two handshake frames appear.
4. Select `chat-1`; leave `send` on **Reply with value**; set the value's `body`
   to `"HI"`.
5. Select `chat-2`; pick `send`, type `text: hi`, hit **send**.
6. Frame log: `Call send #0` out, `Reply send ok` back with `{ body: "HI", … }`.
   The call form shows the decoded reply.

**See an error cross the wire**

1. Select `chat-1`, switch `send` to **Raise error**, choose `Rejected`, set
   `reason: "nope"`.
2. Call `send` from `chat-2`. Frame log: `CallError send · ordinal 0`. The call
   form shows `Rejected { reason: "nope" }`.

**Handshake refusal** *(stretch for 1e)*

1. With a connection up, edit `chat.ids` so its IR changes, and return to
   simulate *without* rebuilding `chat-2`.
2. The next connection attempt uses mismatched `ir_hash` values;
   `Handshake.check` throws. The log shows both handshake frames then
   `connection refused · handshake`, and the canvas edge goes danger.

## Milestones

Five steps, each independently reviewable and mergeable; each lands with its
acceptance check green.

| # | Step | Acceptance |
|---|---|---|
| **1a** | `describe_project` — WASM fn + `shape.ts`; `ir_hash` matches the generator's `IR_HASH` | `describe_project(sampleFiles)` returns `Chat` with two functions, correct indices, `note` one-way, `send` throws `Rejected` ordinal 0; a Rust test asserts hash equality |
| **1b** | Runtime & wire — vendor `@comline/runtime`; `TappedTransport`, `GenericClient`, `GenericDispatch`; headless | `node --test`: a `send` call and a `Rejected` error round-trip over `duplex()`; the drift-guard test shows identical frames to `chat.ts`; every frame reaches the tap |
| **1c** | Engine & behaviours — `Session`, add / remove / connect, the six behaviours, the serve loop, send routing | from a script: server(Reply) + client, call → constant; flip to Raise error → mapped `SimRemoteError`; flip to Drop → call stays pending |
| **1d** | Canvas & inspector — the simulate view, header switch, drag-to-place, the one connection, per-function behaviour pickers, the arg form + raw-JSON fallback | everything in 1c done entirely through the UI with the sample schemas |
| **1e** | Frame inspector — the frame log (expandable envelopes, hex, framing label, latency, handshake frames); the refusal path | the "two services talk" tutorial beat demonstrable end to end, including a handshake refusal after a schema edit |

## Open questions

- ~~**ir_hash parity**~~ *(resolved in 1a)* — both generators call
  `comline_core::schema::ir::frozen::schema_ir_hash` directly, and
  `describe_project` makes the same call on the same units vec; a wasm-level
  check confirms the values match.
- ~~**Array / collection kinds**~~ *(resolved in 1a)* — `T[]` freezes as
  `KindValue::Namespaced("T[]", None)`; `TypeRef` peels the suffix.
- **Route-B drift** — a second copy of the generator's client/dispatch glue can
  diverge silently; the conformance test against `chat.ts` is the guard.
- **Vendored runtime staleness** — the copy under `sim/runtime/` will not track
  `comline-typescript`; header comment with the source commit, and a note in
  that repo to re-vendor on a contract change.
- **Datagram request-id correlation** — with **Drop** in play, confirm a dropped
  reply leaves the client pending (desired) rather than wedging the next call.
- **Session rebuild on schema change** — keying surviving instances by protocol
  name is a guess at intent; revisit if it feels lossy.

## Deferred to Phase 2+

Named so the Phase 1 model leaves room and reviewers know what is intentionally
missing. All of the below are now specced in
[Playground simulation — Phase 2](playground-simulation-phase-2.md), staged as
milestones 2a–2i.

- Multiple connections, fan-out (one server, many clients), node-to-node
  forwarding, a node hosting several instances.
- User-written behaviour snippets, evaluated in a Worker sandbox.
- Fault injection as first-class controls — drop, delay, reorder, corrupt,
  partition.
- Time control: step, pause, speed; record & replay; a session serialised into
  the URL.
- Datagram vs. JSON-RPC shown side by side for the same call.
- Route A — transpile the generated TypeScript in the browser and run the real
  module as an instance's implementation.
- MessagePack codec; a length-prefixed stream transport.
- Extracting `sim/` as a component the tutorial embeds with a fixed topology per
  lesson.
