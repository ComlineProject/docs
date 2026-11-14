# Proposal C — a connection per package

Status: **accepted** (2026-11-14), complementary to [A](multi-package-connection.md) ·
See the [section overview](index.md) for the question all three answer

**The idea:** each package's protocols run on a connection of their own, with
that package's facts and `comline@2` exactly as written. A dependency's
protocol is served on the dependency's connection, never on the consumer's.

## Shape

```text
connection 1   comline@2, package localdeps 0.2.0   greeting::Foo  #0
connection 2   comline@2, package test 0.4.0        none::Thing    #0
```

Generators already emit a connection per package. A dependency's generated
module gets its own `accept`, `serve` and `connect`, which run `comline@2` with
that package's facts. So C needs no change to the wire, the runtime or the
handshake, only step 0 and the dependency's facts in the request (as
[A](multi-package-connection.md#what-it-touches) needs too).

## What it gives

- **One identity, checked against its own version.** Foo is localdeps' #0
  everywhere, and the handshake compares localdeps' versions.
- **Each package keeps its own encodings.** A dependency on `jsonrpc` and an
  application on `datagram@3` both work, because neither has to fit the other's
  connection. A can't do this.
- **Isolation.** A dependency's handlers can't see the application's
  connection state. A refusal under `scope = package` ends only that
  package's connection. Different trust can sit on different connections: a
  public health check beside an authenticated API.
- **The consumer's version is untouched.** None of the dependency's protocols
  are part of the consumer's connection.
- **Serving in parts across processes.** A dependency's protocols can be served
  by another process or host, since its connection doesn't have to end where
  the application's does.

## What it costs

- **More connections, and finding them.** N packages need N connections:
  N transport setups, TLS sessions and handshakes. A peer must also know where
  each package lives, through separate ports or addresses, or a transport that
  multiplexes streams (QUIC, HTTP/2, WebSocket subprotocols). Multiplexing in
  the transport is A one layer down, without a handshake that sees across
  packages.
- **No shared connection state.** Extensions are per connection. A peer
  authenticates on each one, and Foo's handler can't see the session that
  test's connection established.
- **No order across packages.** A connection runs one call at a time, in
  order. Calls on two connections race. [Phases](../packet-dispatch/index.md) are
  per connection, so a phase can't span packages.
- **No calls back across packages.** With calls in both directions, Foo's
  handler can call only the protocols on its own connection. It can't call
  the application's `Client` protocol on the same peer.
- **Half-connected peers.** One connection can drop while the other stays up,
  and the application has to handle a peer it can reach for one package but
  not the other.

## Partial serving

Serving part of what the packages declare doesn't need C by itself. Within one
connection, both `comline@2` and [A](multi-package-connection.md) handle a
missing protocol as `unknown_protocol`, so a server can provide only some of
them. A can also make that choice per dependency protocol.

C is the answer when the parts are **served in different places**: a
dependency's protocols in another process, or another host, or behind
different trust. Then they need their own connection anyway.

## When it's the choice

- A dependency's protocol whose framing, handshake or format differs from the
  connection's. A refuses it, and C is where it goes.
- A deployment that wants isolation, separate trust, or the dependency served
  elsewhere.

Otherwise A is cheaper for the peer: one transport, one handshake, shared
state and order. Both should be supported, and generators already emit C's
per-package connections. A adds the shared one.
