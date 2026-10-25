# Call systems & serialization

The **call system** (sometimes *CaSy*) is the part of the [runtime](index.md)
that turns an invocation of a [protocol](../idl/protocol.md) function into bytes
on a transport and back again.

It is pluggable along two axes:

- **Call format (framing)** — how a request/response is framed. Three ship
  today: **`datagram@2`** (the default), a compact binary framing for
  [connections](#connections); its lockstep first version, **`datagram`**;
  and [JSON-RPC 2.0](https://www.jsonrpc.org/specification). Framing is
  chosen when code is generated (a protocol's `@framing` annotation, else the
  package's `wire.framing`), not swapped at the call site.
- **Message serialization (wire format)** — how the
  [structures](../idl/structure.md) carried by a call are encoded:
  **[`packed@1`](../../reference/wire/packed.md)** (the default: fixed-width
  fields, no tags or names), JSON, and
  [MessagePack](https://msgpack.org/) (Rust only, for now). The package
  declares it as `wire.format`, and generated code names it `Format`; a
  connection made by hand can pass another.

Both are declared in `config.idp`'s `wire` key
([Wire defaults](../packages/index.md#wire-defaults)).

The runtime handles routing between a caller and the protocol implementation;
you pick the formats that fit your deployment.

## Handshake

Before either side makes a real call, `connect` / `serve` run the
protocol's handshake. Comline's own, `comline@1` (the default), exchanges a
small fixed-size frame declaring the
schema fingerprint both ends were generated from, plus the wire format
and framing in use. A mismatch on any of those — different schema
versions, one end MessagePack and the other JSON, incompatible framing —
is refused immediately, rather than surfacing later as a confusing decode
error partway through a real call. Capability bits are exchanged too, but
a difference there is advisory, not a refusal.

A protocol talking to a peer that can't take part — a legacy service, say —
declares `@handshake = "none"` and says why with `@unverified` (see [Giving up
a guarantee](../idl/protocol.md#giving-up-a-guarantee)); its generated
`connect` / `serve` then skip the exchange. In the runtimes the handshake is
a trait (`Handshake`; an interface in TypeScript), so a custom one can be
passed to `Client::connect_with` / `Server::serve_with` by hand. Hand-wired
code can also skip it at the call site with `Client::new_unverified` /
`Server::serve_unverified` (`Client.unverified` / `serveUnverified` in
TypeScript) — named so that skipping is as visible there as in a schema.

## Connections

A client and a server (the `datagram` framing) work in lockstep: the client
sends a request and reads the next frame as its reply. A **connection**, which
every protocol uses by default, lifts that limit:

- **Either side can call,** since `datagram@2` marks each frame as a request
  or a reply.
- **Several calls can be in flight.** A reply is matched to its call by
  request id.
- **Several protocols share it.** Each frame carries its protocol's number.
- **A side waiting for a reply keeps serving the peer's requests,** so a
  handler can call back the peer that called it.

The runtime keeps the protocol logic in a core that does no I/O: bytes go in,
events come out ("serve this request", "this reply ends call 7"). The
`Connection` around it owns the transport. The handshake is the same as a
client's and a server's; a connection checks one hash over every schema in
the package, which also fixes the protocols' numbers.

Which protocols run on a connection is the schema's choice: see
[Calls in both directions](../idl/protocol.md#calls-in-both-directions).

## Concrete API

This page stays the language-agnostic concept; [Language
Guides](../../languages/index.md) has the concrete, per-language API —
constructing a wire format, picking a framing, and what the handshake
looks like in code.
