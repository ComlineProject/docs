# Playground simulation — Phase 2

Status: **planned** — the staged plan for everything
[Phase 1](playground-simulation.md) deferred. Phase 1 proved one call between two
services on the real `@comline/runtime`. Phase 2 turns that into a place to
reason about *distributed* behaviour: many services and connections, an
unreliable wire, controllable time, user-written behaviour, and — last — the
actual generated module running in the browser. Nine milestones (**2a–2i**),
each independently reviewable and shippable, each landing with its acceptance
check green. Still almost entirely app code over the vendored runtime; the one
`comline-core` touch (a codegen re-export for route A) is called out in
[Open questions](#open-questions). Affects `ComlineProject/playground`, then
`ComlineProject/docs` (the tutorial embeds the result).

## Goal

Phase 1's sentence was *two services generated from the same schema can talk,
and refuse to when they were not*. Phase 2's is:

> the same schema, run as a **system** — many services, a wire that drops and
> delays, time you can step through — behaves the way the protocol says it
> should, and you can watch every frame.

Concretely, by the end of Phase 2 the playground can:

- wire **many** connections at once — one server fanning out to several clients,
  one client talking to several servers, and a **gateway** node that is a client
  of one protocol and a server of another, forwarding calls;
- inject **faults** per connection — drop, delay, reorder, corrupt, partition —
  and see how a generated client copes (timeouts, retries where the schema has
  them, `RuntimeError` surfacing);
- **control time** — step / pause / play / speed — over a virtual clock, so a
  race is inspectable frame by frame;
- **record and replay** a session, and share it as a URL;
- run a **user-written behaviour** for a function in a Worker sandbox instead of
  the six canned ones;
- compare the **same call across framings and codecs** (datagram / JSON-RPC,
  JSON / MessagePack) side by side;
- run **route A** — transpile the generated TypeScript in-browser and use the
  real `<Proto>Client` / dispatcher as an instance's implementation, with route B
  still the default and the drift guard still watching;
- be **embedded** in a tutorial lesson with a fixed, partly-locked topology.

## What changes from Phase 1

Phase 1's [architecture](playground-simulation.md#architecture) holds. Three
core generalisations carry the rest:

| Phase 1 | Phase 2 |
|---|---|
| `Session.connection: Connection \| null` | `Session.connections: Connection[]` — the engine holds a `Map<connId, LiveConnection>` |
| node ≡ instance | a **node** hosts one or more instances; an instance still belongs to exactly one node |
| `TappedTransport` with a fixed `latencyMs` | `TappedTransport` driven by a `FaultSpec` + a `Clock` — delivery is scheduled, not `setTimeout`-d |
| one merged frame log | frames carry `connId`; the log filters/splits by connection |
| behaviour = one of six canned fns | behaviour = canned **or** a sandboxed user snippet, same `Behavior` interface |
| route B only | route B default; route A opt-in per instance |

No change to `describe_project`, the vendored runtime contract, or the drift
guard. `model.ts` / `engine.ts` / `transport.ts` grow; `generic.ts` and
`behavior.ts` gain, not change.

New module layout (added to Phase 1's `app/src/sim/`):

```text
sim/
  clock.ts        virtual clock + scheduler; real-time and stepped modes
  faults.ts       FaultSpec, the per-frame decision (drop/delay/reorder/corrupt)
  topology.ts     Node, multi-instance, the connections[] operations
  record.ts       session ⇄ URL, input capture, replay driver
  sandbox/
    host.ts       Worker lifecycle, the call protocol, timeout/kill
    guest.ts      runs in the Worker: eval the snippet, expose the ctx API
  routea/
    transpile.ts  esbuild-wasm wrapper: generated .ts → an ES module blob
    load.ts       import the module, adapt <Proto>Client / dispatcher to Behavior/engine
  embed.ts        mount(el, { schemas, topology, locked, lesson }) — the tutorial entry
```

## Milestones

| # | Step | Acceptance |
|---|---|---|
| **2a** | **Many connections** — `connections[]`, N live wires, canvas draws & selects N edges, frame log gains a connection column + per-connection filter | fan-out: one `Chat` server, two clients, each calls `send`, both replies correct, the log shows two connections; removing one connection leaves the other live |
| **2b** | **Nodes host many instances + forwarding** — a node with a `client` of `A` and a `server` of `B`; a **Forward** behaviour that calls out on another connection before replying | a `gateway` node relays `B.send` → `A.send` → back; the frame log shows the nested call on the second connection; a cycle is refused |
| **2c** | **Fault injection** — `FaultSpec` per connection: `dropProb`, delay distribution, `reorderWindow`, `corruptProb`, `partition` toggle; inspector controls; log annotations | with `dropProb=1` on responses a `send` call surfaces `RuntimeError("timeout")` after the client's window; clearing the fault, the next call succeeds; a corrupted frame shows `framing: undecodable` |
| **2d** | **Virtual clock** — scheduler over a `Clock`; step / pause / play / speed; deterministic given a seed | with a 200 ms delay fault and the clock paused, `send` is issued, "step" advances one frame at a time, the reply lands only after time is advanced past 200 ms; same seed ⇒ same frame order twice |
| **2e** | **Record & replay + shareable session** — `Session` (topology, behaviours, faults, seed) ⇄ URL; input capture; replay driver | a recorded 3-call session replays to a byte-identical frame log; the URL round-trips a two-node fan-out and reconnects it on load |
| **2f** | **User-written behaviours** — Worker sandbox; a function runs `(params, ctx) => Outcome` with a timeout + a small API; canned behaviours stay | a snippet returning `{ ok: { body: params.text.toUpperCase() } }` drives `send`; an infinite-loop snippet is killed and the call gets `RuntimeError`; the snippet cannot reach `window` / `fetch` |
| **2g** | **Framing / codec matrix** — the same call through datagram + JSON-RPC, JSON + MessagePack, side by side; `MsgPackCodec` | one `send` rendered four ways; the decoded bodies match; the JSON-RPC and datagram request frames differ only as their specs say |
| **2h** | **Route A — run the real module** — `esbuild-wasm` transpiles the generated `.ts`; it loads as an ES module; the generated `<Proto>Client` / dispatcher runs against a browser build of `@comline/runtime` as an instance's implementation; route B stays default | an instance flipped to "route A" serves `send` from the *generated* `ChatDispatcher`; its frames are byte-identical to route B's for the same behaviour (the drift guard, now live in the UI); transpile failure falls back to route B with a notice |
| **2i** | **Embeddable `<sim>`** — `mount(el, { schemas, topology, locked, lesson })`; fixed topology, some controls locked; no header / edit view | the tutorial's "two services talk" lesson embeds the sim with `chat-1` / `chat-2` pre-wired and the palette hidden; a second lesson embeds a fan-out |

2a–2e are the topology-and-time spine and should land in order. 2f (sandbox)
and 2g (matrix) are independent and can interleave. 2h (route A) depends only on
2f's Worker plumbing being available (it runs the transpiled module in a Worker
too) and should come after the drift guard is exercised by the matrix in 2g.
2i is last — it packages a stable surface.

## Topology (2a–2b)

### The model

```ts
interface Node {
  id: string;
  label: string;            // "gateway", "chat-1"
  x: number; y: number;
  instanceIds: string[];    // ≥ 1
}

interface Connection {
  id: string;
  clientId: string;         // an instance id
  serverId: string;         // an instance id
  faults: FaultSpec;        // 2c; identity (no-op) until then
}

interface Session {
  shape: ProjectShape;
  nodes: Node[];
  instances: Instance[];
  connections: Connection[];
  seed: number;             // 2d
}
```

An `Instance` keeps its Phase 1 fields (`role`, `schemaNs`, `protocol`,
`behaviors`, `irHash`) and gains `nodeId`. `addInstance` either makes a fresh
node or, when dropped onto an existing node, appends to it — a node badge shows
the count.

### Connection rules

- client and server ends are **instances**, opposite roles, same
  `schemaNs::protocol` (unchanged from Phase 1).
- an instance may be **one end of many connections**: a server with N client
  connections is fan-out; a client with N server connections is fan-in. The
  engine builds one `duplex()` + serve loop **per connection** — a server
  instance in three connections runs three serve loops over three taps, which is
  what three real peers would cause.
- **no duplicate** `(clientId, serverId)` pair.
- a **cycle** through forwarding is refused at call time (see below), not at
  connect time — the topology graph is only a cycle once behaviours forward
  along it.

### The engine

`engine.connectAll(session)` replaces `connect`. It diffs the desired
`connections[]` against the live `Map<connId, LiveConnection>`: opens new ones,
closes removed ones, rebuilds ones whose framing / `irHash` / faults changed.
Each `LiveConnection` keeps its Phase 1 shape plus `connId`. `GenericClient.call`
is now reached as `live(connId).call(fn, params)`; the call form picks the
connection when the selected client has more than one.

### Forwarding (2b)

A **Forward** behaviour on `(serverInstance, fn)`:

```ts
{ kind: "forward",
  config: { viaConnectionId: string; targetFn: string; mapParams?: string /* jsonata-lite, optional */ } }
```

`run(ctx)` resolves the `LiveConnection` for `viaConnectionId` (which must have
this instance's **node** as its client end), calls `targetFn` with the params
(mapped if `mapParams` is set), and returns the downstream outcome as its own —
an `ok` becomes an `ok`, a `SimRemoteError` becomes an `err` with the same
ordinal. The frame log shows the downstream `Call` / `Reply` on the second
connection, indented under the first. A forward that would re-enter a connection
already on the call stack fails with `RuntimeError("forwarding cycle")` — the
stack is carried on the `BehaviorCtx`.

This is enough for a **gateway / proxy** demo: a node that is
`server of Public` and `client of Internal`, forwarding `Public.request` to
`Internal.handle`.

## Faults (2c)

```ts
interface FaultSpec {
  dropProb: number;         // 0..1, per frame, direction-filterable
  delay: { min: number; max: number };  // ms, uniform; 0..0 = none
  reorderWindow: number;    // hold up to N frames and release shuffled; 0 = ordered
  corruptProb: number;      // 0..1; flips a random byte in the body
  partition: boolean;       // hard cut both directions until cleared
  applyTo: "requests" | "responses" | "both";
}
```

Lives on the `Connection`; the engine hands it to both `TappedTransport`s of
that connection. `TappedTransport.send` becomes: **record the frame** (always,
with a `fault` annotation), then ask the `FaultSpec` + the seeded RNG what to do
— deliver now, deliver after a delay via the `Clock`, hold for reorder, corrupt
then deliver, or drop. A dropped frame is in the log greyed with `dropped`; a
corrupted one decodes to `framing: undecodable` and the receiving runtime raises
`framing` / `serialization` as it would for real.

Partition is the coarse control the tutorial wants for "what happens when the
network splits": every frame both ways is dropped, pending `call`s time out,
and clearing it does **not** replay held frames (a real partition loses them).

Inspector: a **faults** section per selected connection with the five controls;
a connection with any active fault draws its edge dashed-amber.

## Time (2d)

Phase 1 delivers with `setTimeout`. Phase 2 routes every delayed delivery
through a `Clock`:

```ts
interface Clock {
  now(): number;
  after(ms: number, fn: () => void): () => void;  // returns a cancel
  mode: "real" | "stepped";
}
```

- **real** — `after` is `setTimeout`; `now` is `performance.now()`. The default;
  identical to Phase 1 behaviour.
- **stepped** — a priority queue of `(dueAt, fn)`. "step" pops the earliest and
  runs it; "play" drains at `speed × wall time`; "pause" stops draining. `now`
  is the virtual time, advanced to each entry's `dueAt` as it fires.

The engine, the fault delays, and the sandbox timeout all take the same `Clock`.
Determinism: in stepped mode with a fixed `seed`, the fault RNG and the queue
order are fully determined, so a session's frame log is reproducible — the basis
for record & replay.

Controls sit in the frames header: `⏸ ▶ ⏭` and a speed select. A stepped clock
with pending entries shows a count (`3 events queued`).

## Record & replay, shareable sessions (2e)

**Serialisation.** `Session` minus `shape` (which is recomputed from the
schemas) serialises to compact JSON → deflate → base64url → the URL fragment.
On load, if a `#s=` fragment is present and the current schemas produce a
matching set of `ir_hash`es, the topology is restored and connected; on a hash
mismatch the instances load **stale** (Phase 1's resync flow applies).

**Recording** captures the ordered list of user inputs — `call(connId, fn,
params)`, behaviour edits, fault edits, clock steps — each stamped with the
virtual `now`. **Replay** loads the session, forces `clock.mode = "stepped"`,
and feeds the inputs back at their timestamps. With the same seed the frame log
is byte-identical; this is the acceptance check and a regression guard for the
engine.

The frames header gains `● rec` / `▷ replay`. A recording exports as a JSON file
and imports back.

## User-written behaviours (2f)

A seventh behaviour kind, **Script**:

```ts
{ kind: "script", config: { source: string } }
```

`source` is an ES module body that default-exports
`async (params, ctx) => Outcome`, where `Outcome` is Phase 1's
`{ ok } | { err: { ordinal, data } } | { none: true }` and `ctx` exposes only:

```ts
interface ScriptCtx {
  fn: FnShape;                 // the function being served (read-only)
  proto: ProtocolShape;
  state: Record<string, unknown>;  // persists across calls on this instance
  sleep(ms: number): Promise<void>;   // via the engine Clock
  log(...args: unknown[]): void;       // to the frame log's side channel
}
```

**Sandbox.** One `Worker` per scripted instance. `host.ts` posts
`{ params }`; `guest.ts` `import()`s a blob URL of the source once, caches the
export, runs it, posts back the `Outcome` or an error. No `window`, `fetch`,
`XMLHttpRequest`, `WebSocket`, or dynamic `import` of anything but the initial
blob — enforced by running the guest with those globals shadowed to `undefined`
and a CSP on the worker. A call that exceeds `scriptTimeoutMs` (clock-driven)
terminates the Worker and returns `RuntimeError("timeout")`; the Worker respawns
for the next call.

The inspector shows a small code editor (reuse the CodeMirror setup already in
the app) with the `ScriptCtx` type surfaced as a doc comment. A syntax error is
reported inline and the behaviour falls back to **Drop** until fixed.

Not in scope: importing packages, multiple files, TypeScript types on the
snippet (it is plain JS). Those are Phase 3 if wanted.

## Framing / codec matrix (2g)

A **compare** panel: pick a client, a function, params once, and the engine runs
the call over a throwaway connection in each of `{datagram, jsonrpc} ×
{json, msgpack}`, showing the four frame sets in columns with a shared body view.
It asserts the decoded request params and the decoded reply are equal across all
four; divergence is a bug in a framing or codec.

`MsgPackCodec` implements the vendored `Codec` interface (`name: "msgpack"`,
`encode`/`decode`) with a small dependency-free MessagePack pair vendored
alongside the runtime. It does **not** need `comline-typescript` to gain
MessagePack — the sim's codec is its own; a note goes in the runtime repo that a
real one would live there.

## Route A — run the real module (2h)

The playground already generates the TypeScript (`generate_project`, the
"generated" tab). Route A runs it.

1. **Transpile.** `esbuild-wasm` (loaded once, ~3 MB, lazy) compiles the
   generated `.ts` — client + dispatcher + the schema's types — to one ES
   module, rewriting the `@comline/runtime` import to a blob URL of a **browser
   build of the vendored runtime** (the runtime is dependency-free ES already;
   this is a bundling step, not a port).
2. **Load.** `import(blobUrl)` gives the real `ChatClient`, `serveChat`,
   `ChatDispatcher`.
3. **Adapt.** For a **server** instance on route A, `serveChat(impl, transport,
   codec, framing)` replaces `GenericDispatch` — `impl` is built from the
   instance's behaviours (a canned behaviour becomes a generated-signature method;
   a **Script** behaviour is called through the same sandbox). For a **client**
   instance, `ChatClient` replaces `GenericClient`.
4. **Guard.** The Phase 1 drift guard becomes a **live** check: with an instance
   on route A and its peer on route B and the same behaviour, the frame logs
   must stay byte-identical. A mismatch is surfaced in the UI, not just CI.

Route A is opt-in per instance (a toggle in the inspector), defaults off, and
falls back to route B with a notice if transpilation fails or `esbuild-wasm`
will not load. It is the riskiest milestone — if `esbuild-wasm` size or
cross-origin-isolation requirements make it impractical on GitHub Pages, 2h
ships as "route A behind a flag, not in the default bundle" and the rest of
Phase 2 stands without it.

## Embeddable `<sim>` (2i)

`embed.ts` exports:

```ts
mount(el: HTMLElement, opts: {
  schemas: FileInput[];           // fixed for the lesson
  topology?: SerializedSession;   // pre-wired nodes / connections
  locked?: ("palette" | "connections" | "behaviours" | "faults" | "schemas")[];
  lesson?: string;                // analytics / deep-link id
}): { destroy(): void }
```

It mounts the canvas + inspector + frame log without the header or the edit
view, honours `locked` (a locked control renders read-only), and never touches
the URL fragment (the host page owns that). The tutorial's runtime-demo lesson
embeds it with `chat-1` / `chat-2` pre-wired and `palette` + `schemas` locked;
a later lesson embeds a fan-out with `connections` unlocked so the reader adds
the third client.

This is the point where `sim/` gets a stable public surface and a short
`README`; until 2i it is internal to the app.

## Open questions

- **Serve-loop cost at fan-out** — one server instance in N connections runs N
  serve loops. Fine for the ~single-digit N a demo shows; note a ceiling and a
  friendly error past it rather than letting the tab hang.
- **`esbuild-wasm` on GitHub Pages** *(blocks 2h's default-on)* — size (~3 MB)
  and whether it needs `SharedArrayBuffer` / cross-origin isolation, which
  Pages does not set. Fallback: `sucrase` (smaller, strips types only, no
  bundling) with a hand-written import shim, or route A stays flag-only.
- **`comline-core` touch for route A** — the transpile step needs the generated
  files *and* their intended import graph. `generate_project` already returns
  the file set; confirm it also returns enough for the `@comline/runtime`
  import rewrite (it should — the import is a fixed string). If a re-export or
  a manifest field is missing, that is the one small core/codegen change in
  Phase 2.
- **Reorder + virtual clock interaction** — a reorder window holds frames until
  N accumulate or a timeout; in stepped mode "timeout" is virtual, so a held
  frame needs a queue entry. Confirm the release rule reads cleanly when time is
  paused (probably: release on step if the window is non-empty and no more
  frames are pending).
- **Script `state` across a rebuild** — a schema edit rebuilds instances; does a
  scripted instance keep its `state`? Lean yes while `schemaNs::protocol`
  survives, same as behaviour configs.
- **Record format stability** — the replay guard only holds if the record
  format and the engine's input handling stay in lockstep; version the record
  JSON and refuse a mismatched one rather than replaying it wrong.

## Risks and cuts

- If 2h (route A) proves impractical, Phase 2 still delivers 2a–2g + 2i and the
  drift guard stays CI-only — the sim remains a faithful re-implementation, just
  not the literal module.
- 2d (virtual clock) is the highest-leverage / highest-churn change — it touches
  every delayed path. If it slips, 2c ships with real-time-only faults and 2e's
  replay is "best effort, not byte-identical" until 2d lands.
- The sandbox (2f) is a security surface. Keep the guest globals denylist and
  the worker CSP under test; a snippet reaching the network is a release
  blocker.

## Not in this phase

- Package imports / multi-file / TypeScript in Script behaviours.
- A real MessagePack codec in `comline-typescript` (the sim vendors its own).
- Length-prefixed stream transport (Phase 1's `duplex()` is message-oriented;
  a byte-stream transport with its own framing is Phase 3).
- Persisting sessions server-side; only the URL fragment and file export.
- More than one schema project open at once in the sim.
