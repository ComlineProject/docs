# Call systems & serialization

The **call system** (sometimes *CaSy*) is the part of the [runtime](index.md)
that turns an invocation of a [protocol](../idl/protocol.md) function into bytes
on a transport and back again.

It is pluggable along two axes:

- **Call format (framing)** — how a request/response is framed. Two ship
  today: a compact binary **datagram** framing (the default), and
  [JSON-RPC 2.0](https://www.jsonrpc.org/specification). Framing is chosen
  when code is generated (a protocol's `@framing` annotation, or the
  package's default), not swapped at the call site.
- **Message serialization (wire format)** — how the
  [structures](../idl/structure.md) carried by a call are encoded. JSON and
  [MessagePack](https://msgpack.org/) ship for Rust; JSON ships for
  TypeScript. Unlike framing, this is a runtime choice — passed to the
  client/server when a connection is made.

The runtime handles routing between a caller and the protocol implementation;
you pick the formats that fit your deployment.

## Handshake

Before either side makes a real call, `connect` / `serve` (the
handshaking variants) exchange a small fixed-size frame declaring the
schema fingerprint both ends were generated from, plus the wire format
and framing in use. A mismatch on any of those — different schema
versions, one end MessagePack and the other JSON, incompatible framing —
is refused immediately, rather than surfacing later as a confusing decode
error partway through a real call. Capability bits are exchanged too, but
a difference there is advisory, not a refusal.

A non-handshaking path (`Client::new` / `Server::serve` on the Rust side)
exists for peers that can't take part in it — a legacy service, say — at
the cost of losing that up-front check.

## Concrete API

This page stays the language-agnostic concept; [Language
Guides](../../languages/index.md) has the concrete, per-language API —
constructing a wire format, picking a framing, and what the handshake
looks like in code.
