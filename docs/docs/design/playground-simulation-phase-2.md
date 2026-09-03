# Playground simulation — Phase 2

Status: **in progress** — 2a–2f and the full engine port are done, as PRs #1–#10
against [`ComlineProject/simulator`](https://github.com/ComlineProject/simulator).
Remaining: 2g (framing / codec matrix), rewiring the playground UI onto the new
engine, and 2i (the tutorial embed). 2h is **subsumed** — see below.

Phase 1 proved one call between two services on the real `@comline/runtime`.
Phase 2 turns that into a place to reason about *distributed* behaviour: many
services and connections, an unreliable wire, controllable time, user-written
behaviour, and the shareable, replayable session.

> **Architecture changed mid-phase (2026-09).** Phase 1–2a–2e were built as
> TypeScript inside `ComlineProject/playground`, over a *vendored copy* of
> `@comline/runtime` plus a re-implementation of the generated client / dispatch
> glue. That grew large enough to be its own thing. The engine is now
> [`ComlineProject/simulator`](https://github.com/ComlineProject/simulator) — a
> Rust crate → WASM — and the playground / tutorial / docs are thin hosts over
> its `Sim` `wasm-bindgen` surface. This retires the vendored port, the
> re-implementation, and the drift guard, and it collapses milestone 2h. The
> sections below are updated to match; [Architecture](#architecture-the-engine-is-its-own-crate)
> is new.

## Goal

Phase 1's sentence was *two services generated from the same schema can talk, and
refuse to when they were not*. Phase 2's is:

> the same schema, run as a **system** — many services, a wire that drops and
> delays, time you can step through — behaves the way the protocol says it
> should, and you can watch every frame.

Concretely, by the end of Phase 2 the playground can:

- wire **many** connections at once — one server fanning out to several clients,
  one client talking to several servers, and a **gateway** node that is a client
  of one protocol and a server of another, forwarding calls;
- inject **faults** per connection — drop, delay, reorder, corrupt, partition —
  and see how a client copes (timeouts, `RuntimeError` surfacing);
- **control time** — step / advance / play — over a virtual clock, so a race is
  inspectable frame by frame;
- **record and replay** a session, and share it as a URL;
- run a **user-written behaviour** for a function as a sandboxed Rhai script
  instead of only the canned ones;
- compare the **same call across framings and codecs** (datagram / JSON-RPC,
  JSON / MessagePack) side by side;
- be **embedded** in a tutorial lesson with a fixed, partly-locked topology.

## Architecture — the engine is its own crate

The simulation engine is
[`ComlineProject/simulator`](https://github.com/ComlineProject/simulator), a Rust
crate compiled to WASM. The host (playground, tutorial, docs) provides the UI and
drives it through the `Sim` `wasm-bindgen` surface — construct from a compiled
shape, edit the topology, drive calls, read the frame log, record / replay.

**Why a separate crate.**

- It builds against **`comline-runtime` directly** (the `alloc` tier — `no_std`,
  allocation-free, synchronous). No vendored port of the TS runtime, no
  re-implementation of the generated client / dispatch glue, no drift guard.
- The synchronous contract makes the engine a **discrete-event simulation**: one
  event queue whose time *is* the virtual clock. A call schedules a
  request-delivery event and settles later; there are no promises to interleave,
  so the 2c / 2d timing races the TS version fought simply cannot occur.
- Being a *separate* WASM module from the playground's editor wasm means the
  schema crosses the boundary as bytes regardless. It crosses as the **`Shape`
  JSON** the editor's `describe_project` already emits — a small, stable
  projection — rather than by linking `comline-core` (which would put a second
  copy of the compiler in the bundle). See `src/shape.rs`.

**Module layout** (`ComlineProject/simulator/src/`):

```
rng.rs           seeded PRNG (mulberry32), bit-for-bit with the JS reference
faults.rs        the unreliable-wire spec + transforms
frame.rs         the frame tap the inspector reads
format.rs        the JSON WireFormat
shape.rs         the compiled-project projection (describe_project mirror)
clock.rs         the virtual clock + its event queue
wire.rs          one connection's tapped, fault-injecting channel
behavior.rs      the 8 server behaviours (reply … forward, script)
generic.rs       a dispatcher driven by a ProtocolShape, no codegen
model.rs         the Session: nodes, instances, connections, ops
session_codec.rs the Session ⇄ #s=… shareable link
record.rs        record & replay
engine.rs        many connections over one clock; the discrete-event pump
framedecode.rs   a raw frame → the inspector's decoded view
facade.rs        the #[wasm_bindgen] Sim surface
```

**Scripting is a cargo feature** (`script`, default on) — it pulls Rhai, which
~5× the wasm (445 KB → ~2.1 MB; ~165 → ~580 KB gzipped). `--no-default-features`
keeps the lean build for the tutorial embed. See the simulator repo's `README`
for the current lazy-load thinking.

## What changes from Phase 1

Three core generalisations carry the rest:

| Phase 1 | Phase 2 |
|---|---|
| `Session.connection: Connection \| null` | `Session.connections: Connection[]` — the engine holds one live wire per connection, diffed against the session |
| node ≡ instance | a **node** hosts one or more instances; an instance still belongs to exactly one node |
| transport with a fixed `latencyMs` | a tapped `Channel` driven by a `FaultSpec` + the clock — delivery is a scheduled event, not `setTimeout` |
| one merged frame log | frames carry a connection id; the log filters / splits by connection |
| behaviour = one of six canned fns | behaviour = one of seven canned fns **or** a sandboxed Rhai script, same `Behavior` trait |

## Milestones

| # | Step | Acceptance | Status |
|---|---|---|---|
| **2a** | **Many connections** — `connections[]`, N live wires, canvas draws & selects N edges, per-connection frame log | fan-out: one `Chat` server, two clients, both replies correct, log shows two connections; removing one leaves the other live | ✅ |
| **2b** | **Nodes host many instances + forwarding** — a gateway node; a **Forward** behaviour that calls out on another connection before replying | a gateway relays `B.send` → `A.send` → back; the log shows the nested call; a cycle is refused | ✅ |
| **2c** | **Fault injection** — `FaultSpec` per connection: drop / delay / reorder / corrupt / partition; a client call timeout | `dropProb=1` on responses → the call times out and the wire goes `dead`; clearing the fault + `rebuild` restores service; a corrupted frame reads `framing: undecodable` | ✅ |
| **2d** | **Virtual clock** — the discrete-event queue; step / advance / play; deterministic given a seed | a delay fault + stepped clock: `send` is issued, `step` fires one event at a time, the reply lands only after time passes the delay; same seed ⇒ same frame order twice | ✅ |
| **2e** | **Record & replay + shareable session** — `Session` ⇄ `#s=…` link; input capture; replay | a recorded session replays to a byte-identical frame log; a link round-trips a fan-out and reconnects it | ✅ |
| **2f** | **User-written behaviours** — a sandboxed **Rhai** script as an 8th behaviour kind; the canned ones stay | a script returning `#{ body: params[0] }` drives `send`; an infinite-loop script is stopped (operations limit), not hung; `state` persists between calls | ✅ |
| **2g** | **Framing / codec matrix** — the same call through datagram + JSON-RPC, JSON + MessagePack, side by side | one `send` rendered four ways; the decoded bodies match; the JSON-RPC and datagram request frames differ only as their specs say | ▫ next |
| **2h** | ~~Route A — transpile the generated TS in-browser~~ | — | **subsumed** — the Rust engine already runs the real `comline-runtime` contract; there is no re-implementation to reconcile |
| **2i** | **Embeddable `<sim>`** — a fixed, partly-locked topology; no header / edit view; the lean (`--no-default-features`) wasm | the tutorial's "two services talk" lesson embeds the sim with `chat-1` / `chat-2` pre-wired and the palette hidden | ▫ |

Also on the list before Phase 2 closes: **rewire the playground UI** — replace
`app/src/sim/*.ts` with a thin view over `Sim`, and delete the vendored
`@comline/runtime` + the drift-guard test.

## Topology (2a–2b)

### The model

`Session` holds `nodes`, `instances`, `connections`, plus `latencyMs`,
`callTimeoutMs`, `seed`, and a `clockMode` preference. A `Node` is a canvas box
with `instanceIds` (≥ 1). A `Connection` is `{ clientId, serverId, faults }`
between two instances. An `Instance` keeps its Phase 1 fields (`role`,
`schemaNs`, `protocol`, `behaviors`, `irHash`) and gains `nodeId`. The id
counters live *in* the session (not module globals), so a decoded link keeps
allocating fresh ids without collision.

`shape` is dropped from the serialized form and recomputed from the open schemas
on load; the behaviour map serializes in a stable key order.

### Connection rules

- client and server ends are **instances**, opposite roles, same
  `schemaNs::protocol`.
- an instance may be **one end of many connections** — fan-out / fan-in. The
  engine runs one tapped channel + dispatcher per connection.
- **no duplicate** `(clientId, serverId)` pair.
- a **cycle** through forwarding is refused at call time, not at connect time.

### The engine

`engine.sync(session)` diffs `session.connections` against the live wire set:
opens the ones that appeared, closes the ones that vanished, leaves the rest
running. `engine.rebuild(session)` closes everything and re-opens — for a schema
edit, a latency change, or a replay — re-seeding the fault RNG so a stepped run
from `session.seed` is reproducible. Each wire records a real 31-byte handshake
frame each way and refuses (`connectionError == "handshake"`) on an IR-hash
mismatch — the version-skew demo, decided directly rather than via an async
exchange.

A call doesn't block: `engine.call(connId, fn, params)` frames the request,
schedules its delivery, and returns a request id; the outcome lands later and
`engine.result(id)` reads it (`ok` / `err` / `undecodable` / `timeout`).

### Forwarding (2b)

A **Forward** behaviour on `(serverInstance, fn)` carries
`{ viaConnectionId, targetFn }`. When dispatched it yields a `Forward` step; the
engine relays the call on `viaConnectionId` and, when that inner call settles,
answers the outer one with its outcome — an `ok` stays `ok`, an `err` keeps its
ordinal. A `forwarding` set carries the connections currently mid-relay; a
forward that re-enters one is refused with a `forwarding cycle` error. There is
no parked stack frame — the outer request is answered from a continuation keyed
by the inner call's request id.

This is enough for a **gateway / proxy** demo: a node that is `server of Public`
and `client of Internal`, forwarding `Public.request` to `Internal.handle`.

## Faults (2c)

`FaultSpec` on the `Connection`: `dropProb`, `delayMin` / `delayMax`,
`reorderWindow`, `corruptProb`, `partition`, `applyTo`
(`requests` / `responses` / `both`). The engine hands it to the connection's
`Channel`; the inspector edits it in place with no reconnect.

`Channel.send` records the frame (always, with a `fault` annotation), then decides
against the spec + the seeded RNG: deliver now, deliver after a delay scheduled on
the clock, hold for reorder, corrupt then deliver, or drop. RNG draws are
consumed in a fixed order so a stepped run is reproducible. A dropped frame is in
the log annotated `dropped`; a corrupted one decodes to `framing: undecodable`.
Partition cuts every frame both ways (handshakes included) and does not replay
held frames when lifted.

**Timeout / dead.** A non-one-way call schedules a timeout at
`callTimeoutMs`. If no reply lands, the call settles `timeout` and the wire goes
`dead` — every later call on it fails fast until `engine.rebuild`. A forwarded
inner call that times out propagates an error to the outer, and both wires die.
The clock's `schedule` returns a handle so a call that settles early cancels its
pending timeout (otherwise a far-future timeout would keep the sim "busy" and
over-advance virtual time).

## Time (2d)

There is one clock — a virtual time value plus a `(due, seq)`-ordered event
queue, generic over the event payload. There is no real-time / stepped *engine*
split; the host decides how fast to advance:

- **drain** (`run`) — pop events until the queue is empty; the idiom for a test
  or a settled call.
- **advance(ms)** — fire every event due within the window (including ones
  scheduled while firing), then park time at the edge; the
  `requestAnimationFrame` / playback path.
- **step** — fire the single earliest event.

`clockMode` on the `Session` records the user's preference for the UI; the engine
is always stepped. Determinism: a fixed `seed` + the queue order fully determine
a session's frame log — the basis for record & replay.

## Record & replay, shareable sessions (2e)

**Link.** `Session` minus `shape`, wrapped in a `{ v: 1, session }` envelope →
JSON → base64url → the `#s=` fragment. On decode the current shape is
re-injected and the id counters are lifted past everything loaded; instances keep
their stored `irHash`, so a schema that has moved on since the link was made
loads them *stale* and the resync flow applies. Scalars default leniently
(`callTimeoutMs` 3000, `seed` 1, `real` mode) so a hand-made link still decodes.

**Recording** captures the ordered user inputs — a call, a behaviour edit, a
fault edit — each stamped with the clock time it happened at, relative to
record-start, plus the session link at record-start.

**Replay** decodes the snapshot, forces stepped mode, rebuilds, and for each
event advances to its time, applies the input, and drains what it scheduled. The
discrete-event clock makes this deterministic by construction — no
`Promise.allSettled` / microtask scaffolding. The frame log is byte-identical
across runs; that equality is the engine's regression guard.

## User-written behaviours (2f)

An 8th behaviour kind, **Script** — `{ kind: "script", config: { source } }`
where `source` is a Rhai program.

In scope: `params` (the decoded request) and `state` (a map that persists between
calls on this instance). The last expression is the reply; `throw` raises an
error (ordinal 0, `{ error: <message> }`). A one-way function still sends nothing.
`state` survives a `rebuild` while the instance's `schemaNs::protocol` does, same
as the canned behaviour configs.

**Sandbox.** Rhai has no file / network / process API to reach for, so the
sandbox is about bounding work and memory: `max_operations` (200k),
`max_call_levels`, `max_expr_depths`, and string / array / map size caps;
`print` / `debug` are silenced; the engine is built `no_module` (no script
`import`). An infinite loop hits the operations limit and errors — it does not
hang the sim. A script that does not compile errors at run time with the compiler
message. This is why Rhai was chosen over a JS-snippet-in-a-Worker: safe by
construction, and no cross-thread call protocol.

Behind the `script` cargo feature. Without it the variant still exists but its
factory returns a stub that reports scripting is off, and the wasm stays lean.

Not in scope: importing modules, multiple files, a type-checked script surface.

## Framing / codec matrix (2g)

A **compare** view: pick a client, a function, params once, and run the call over
a throwaway connection in each of `{datagram, jsonrpc} × {json, msgpack}`,
showing the four frame sets side by side with a shared body view. It asserts the
decoded request params and the decoded reply are equal across all four;
divergence is a bug in a framing or a codec.

This lands in the crate: a JSON-RPC `Framing` alongside `DatagramFraming`, and a
MessagePack `WireFormat` alongside the JSON one. The `Shape` already carries a
protocol's `framing`; the engine's per-wire framing becomes a small enum instead
of hard-wired datagram, and `framedecode` gains the JSON-RPC path (its
`DecodeCtx` already takes the framing).

## Embeddable `<sim>` (2i)

The tutorial mounts the sim with a fixed topology and some controls locked, no
header or edit view, and never touching the URL fragment. Because the engine is
already a packaged crate with a `Sim` facade, "embed" is mostly a host-side view:
the tutorial links the **lean** (`--no-default-features`) wasm, ships a
precompiled `Shape` and a session link for the lesson, and renders a cut-down
canvas + inspector + frame log over it.

## Open questions

- **Serve cost at fan-out** — one server instance in N connections runs N
  dispatchers over N taps. Fine for the single-digit N a demo shows; note a
  ceiling and a friendly error past it.
- **Scripting wasm size** — ~580 KB gzipped for the `script`-on build. Accepted
  for now. The playground rewire decides: default on, or ship lean and lazy-load
  the scripted wasm when a `Script` behaviour is selected. The tutorial always
  builds lean.
- **Playground rewire scope** — how thin the TS view actually gets. Everything
  stateful (topology, engine, clock, recorder) moves behind `Sim`; the TS keeps
  the canvas, the inspector forms, the frame-log rendering, and the CodeMirror
  editor for scripts.

## Not in this phase

- Module imports / multi-file / a typed surface in Script behaviours.
- A length-prefixed byte-stream transport (the channel is message-oriented).
- Persisting sessions server-side; only the URL fragment and file export.
- More than one schema project open at once in the sim.
