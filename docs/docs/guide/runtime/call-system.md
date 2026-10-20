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

## Concrete API

This page stays the language-agnostic concept; [Language
Guides](../../languages/index.md) has the concrete, per-language API —
constructing a wire format, picking a framing, and what the handshake
looks like in code.
