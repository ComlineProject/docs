# Framing & wire format

[Call systems & serialization](../../guide/runtime/call-system.md) covers
the concept; this is the concrete TypeScript API.

## Framing

Both framings are implemented and wire-compatible with the Rust runtime:
`DatagramFraming` (the default) and `JsonRpcFraming`. Which one a
generated `<Proto>Client` / `serve<Proto>` uses is decided at generation
time from the protocol's `@framing` annotation or the package's
`default_framing` — exactly as on the [Rust
page](../rust/framing-and-wire-format.md) — and both take an optional
`framing` constructor argument if you want to override it when wiring a
`Client` / `Server` by hand:

```typescript
import { Client, JsonRpcFraming } from "@comline/runtime";

const client = await Client.connect(transport, codec, handshake, new JsonRpcFraming());
```

## Wire format

Only `JsonCodec` ships today — there's no MessagePack codec for
TypeScript yet (the Rust runtime's `MsgPack` has no counterpart here).
Every `Codec` implements `name` (used in the handshake) plus `encode` /
`decode`; `JsonCodec`'s `name` is `"json"`.

```typescript
import { JsonCodec } from "@comline/runtime";

const client = await ChatClient.connect(transport, new JsonCodec());
```

## Shipped combinations

Narrower than Rust's, for the same reason — no MessagePack codec yet:

| Framing | Wire format | Ships |
|---|---|---|
| `datagram` | `json` | ✅ |
| `datagram` | `msgpack` | — no MessagePack codec yet |
| `jsonrpc` | `json` | ✅ |
| `jsonrpc` | `msgpack` | — JSON-RPC's own spec is JSON text |

A TypeScript client and a Rust server (or vice versa) interoperate on any
row both sides support — the handshake, framings, and `JsonCodec` are
byte-compatible with the Rust runtime by design, cross-checked against
its reference vectors.
