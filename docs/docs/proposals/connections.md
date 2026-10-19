# Connections

Status: **under discussion** · tracked in
[runtime#19](https://github.com/ComlineProject/runtime/issues/19) · partly
decided, nothing implemented

**The question:** what a connection carries beyond one client calling one
server, and how the runtime models it. This page covers calls in both
directions and per-connection state. Several protocols on one connection is
next, and will extend it.

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

## Open questions

- **Several protocols on one connection** (next): how protocols are addressed
  on a shared connection, and how this page's `Connection` holds several
  dispatchers and senders.
- **Streams:** their IR representation, flow control, cancellation.
- **Declared policies** ([core#128](https://github.com/ComlineProject/core/issues/128)).
- **Which interceptors ship with Comline,** if any, and in which crate or
  package.

## What it touches

- **Runtime** (Rust and TypeScript): the sans-IO core, `Connection`, its
  blocking and async wrappers, extensions and interceptor hooks, `datagram@2`
  and its conformance vectors, the `duplex` requirement in the handshake.
- **Generators:** provider registration on a connection, per-connection
  senders, the connection handle in handlers, `@provider = Client`.
- **Core:** `@provider` as a known annotation (from
  [packet dispatch](packet-dispatch.md)), and the build error for reverse calls
  under `datagram@1`.
- **Docs:** the runtime guide.
