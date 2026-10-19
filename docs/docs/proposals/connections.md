# Connections

Status: **under discussion** · tracked in
[runtime#19](https://github.com/ComlineProject/runtime/issues/19) · partly
decided, nothing implemented

**The question:** what a connection carries beyond one client calling one
server, and how the runtime models it. This page covers calls in both
directions, per-connection state, and several protocols on one connection.

## Where things stand

- **Rust `Client` works in lockstep** (`runtime/core/src/client.rs`). It sends a
  request and expects the very next frame to be that request's reply.
- **Rust `Server` only replies** (`runtime/core/src/serve.rs`). It reads a
  request, dispatches it and answers, and never starts a send.
- **TypeScript works the same way.** `Client.call` awaits the next `recv`, so
  two concurrent calls on one TS client can take each other's replies.
- **A datagram frame doesn't say whether it's a request or a reply.** A request
  starts with a `u16` call id and a reply with a `u64` request id, so an
  unprompted frame from the server would be misread as a reply.
- **Nothing generates server-to-client protocols.** `@provider = Client`
  ([packet dispatch](packet-dispatch.md#direction-provider-and-consumer)) has
  no runtime to run on.

So server push is three gaps: a frame kind, something reading the connection
all the time, and a generated API for calls the other way.

## Calls in both directions

Decided with the user (2026-10-20):

1. **Reverse calls, not streams.** With `@provider = Client`, the side that
   accepted the connection calls functions the side that dialled provides:
   ordinary calls, one-way or with a reply. Streams (a function returning a
   stream, open in the
   [target contract](../design/core-target-contract.md#47-still-open-beyond-the-above))
   need an IR representation and flow control, and are designed separately.
2. **A transport-independent core under a `Connection`.**
   - **The core** is a state machine: bytes go in, events come out ("dispatch
     this request", "this reply completes call 7"). That's the "sans-IO" style
     of rustls, quinn-proto and h11.
   - **A `Connection`** is built on it. It owns the transport and a reading
     loop. Incoming requests go to this side's dispatchers, and replies go to
     its table of pending calls.
   - **Blocking, async and `no_std` APIs** are thin wrappers over the one core,
     so an async runtime doesn't mean writing `Client` and `Server` again. The
     core stays allocation-free, as the
     [target contract](../design/core-target-contract.md) requires.
   - **Client and server become roles** at connect time: who dialled, and who
     answers the handshake offer
     ([`comline@2`](extensibility.md#comline2-and-its-parameters)).
3. **Calls can nest.** While handling a call, a provider may call its peer and
   wait for the answer, as a language server asks the editor for
   `workspace/configuration` mid-request. So **a side waiting for a reply
   keeps serving incoming requests.** The core gives this without extra work.
4. **The generated API:**
   - **The providing side** registers its provider on its connection, as a
     server does today.
   - **The consuming side** gets a sender bound to **one connection**: a server
     calling clients has to say which client.
   - **Handlers receive a handle to their own connection,** so they can call
     back the peer that called them.
   - **Broadcasting** to many connections stays application code: a loop over
     connections.
5. **What the wire needs:** a request/reply kind marker, as decided for
   [request ids in both directions](packet-dispatch.md#request-ids-in-both-directions).
   - `jsonrpc@1` works unchanged: a message with `method` is a request.
   - Datagram needs a new version, `datagram@2`, with the marker. Reverse calls
     under `datagram@1` are a build error.
   - `comline.packet@1` is covered: one-way packets need no marker, and
     correlated ones carry it.
6. **Transports that can't carry it are refused up front.** A
   request/response-only transport, such as plain HTTP POST, can't deliver a
   call to the client. A package with any `@provider = Client` protocol requires
   the `duplex` capability, so a connection without it is refused with a
   reason. Today the handshake's capability bits are advisory only.

## Per-connection state and interceptors

Decided with the user (2026-10-20). With a `Connection` object, per-connection
state has a home. It splits by how much Comline has to know:

| | What | Defined by |
|---|---|---|
| **Identity and state** | A connection id the runtime assigns; peer information from the transport (address, TLS identity); typed user data attached to the connection (`conn.extensions().insert(Session { … })`, like `http::Extensions`). Handlers reach it through their connection handle. | The runtime |
| **Interceptors** | Composable layers, in the style of tower, at two levels: **frames**, before decode and after encode (traffic inspection, byte counts, compression, logging), and **calls**, after decode (auth checks, rate limits, metrics, tracing). A layer passes a call on, rejects it, or delays it. | The runtime ships the hook points and perhaps a few common layers; policies like rate limiting are user or library code |
| **Declared policies** | Something like `@rate_limit` on a function, so consumers see the limit in the contract and generated clients can pace themselves | The schema. **Later and separate** ([core#128](https://github.com/ComlineProject/core/issues/128)) |

- **This follows the extensibility principle** that transports and dispatchers
  stay runtime-only
  ([Transports and dispatchers](extensibility.md#transports-and-dispatchers)).
  Only declared policies would ever reach the schema.
- **A rejection by an interceptor is a provider fault on the wire,** and the
  reason stays local. The [fault channel](../guide/idl/error.md) already
  exists, and a peer shouldn't learn why it was refused, just as a provider
  fault carries no message.

## Several protocols on one connection

Today a `Server` serves one `Dispatch`. A request names only its function, by
position (datagram) or bare name (JSON-RPC), and the handshake covers one
schema. Error ids are positions across a whole schema, so two schemas sharing a
connection could give two different errors the same number.
[Packet dispatch](packet-dispatch.md) already assumes several protocols per
connection: its families are protocols with an id, and its phases are per
connection.

How other systems name a call's target:

| How a call names its target | Used by |
|---|---|
| **A path string** | gRPC (`/pkg.Service/Method` over HTTP/2), Thrift's multiplexed protocol (`"Service:method"`), LSP's `textDocument/hover` convention, WAMP URIs |
| **A numeric id per interface, plus the method number** | Cap'n Proto (a 64-bit interface id and a method number), MMO opcode families |
| **Stable names agreed at setup, short numbers in each frame** | MQTT 5 topic aliases, HTTP/2 header compression (HPACK), SSH channel numbers |
| **Object path + interface + member** | D-Bus |
| **Interfaces handed out at runtime as references** | Cap'n Proto capabilities |

Decided with the user (2026-10-20):

1. **How a frame names its protocol depends on the framing:**
   - **Comline's own framings: a number the connection hands out.** The
     client's [offer](extensibility.md#comline2-and-its-parameters) lists the
     protocols it wants by stable identity: the package id plus the protocol's
     id or name. The server's answer gives each accepted protocol a
     connection-local number, and frames carry that number, one byte in most
     cases. Protocols from different packages, a dependency's health check
     say, then share a connection with no registry of ids across packages.
   - **Packet framings: the fixed family id** from the schema (`@id` on the
     protocol). The legacy protocol fixes it, and there's no negotiation.
   - **JSON-RPC: a qualified method name** (see 4), because readable names
     are the point of JSON-RPC.
2. **Which protocols a connection carries is negotiated at the handshake:**
   whatever the client offers and the server accepts. A package can
   optionally declare the set allowed together, as a constraint. Interfaces
   handed out by calls at runtime (Cap'n Proto's capabilities) are a larger,
   separate design.
3. **Errors are scoped by their protocol.** A reply identifies its protocol
   (from 1) and the error's position within that protocol, instead of a
   position across the whole schema.
4. **The existing framings:**
   - **`datagram@2`** gains the protocol number. It's a new version anyway,
     for the [request/reply kind marker](#calls-in-both-directions), so both
     changes ship together.
   - **JSON-RPC** gains a framing parameter, `method_names = "bare" |
     "qualified"`. Bare names stay valid for a single protocol; several
     protocols need qualified ones (`"chat.Chat/send"`). It stays `jsonrpc@1`.
5. **The runtime:** the `Connection` holds a table of dispatchers keyed by
   protocol and one sender per protocol (`conn.sender::<Chat>()`). Phases
   decide which entries are active at a given moment.
6. **One protocol shouldn't silently stall the others, but order comes first.**
   The core dispatches **one call at a time** per connection by default, since
   packet protocols rely on order. The async wrapper can offer concurrency,
   per protocol or fully.

## Open questions

- **Streams:** their IR representation, flow control, cancellation.
- **Declared policies** ([core#128](https://github.com/ComlineProject/core/issues/128)).
- **Which interceptors ship with Comline,** if any, and in which crate or
  package.

## What it touches

- **Runtime** (Rust and TypeScript): the sans-IO core, `Connection`, its
  blocking and async wrappers, extensions and interceptor hooks, `datagram@2`
  (kind marker and protocol number) and its conformance vectors, the `duplex`
  requirement in the handshake, protocol numbers handed out by `comline@2`,
  the dispatcher table, JSON-RPC's `method_names`.
- **Generators:** provider registration on a connection, per-connection
  senders, the connection handle in handlers, `@provider = Client`, error ids
  scoped by protocol.
- **Core:** `@provider` as a known annotation (from
  [packet dispatch](packet-dispatch.md)), the build error for reverse calls
  under `datagram@1`, and the optional declared set of protocols.
- **Docs:** the runtime guide.
