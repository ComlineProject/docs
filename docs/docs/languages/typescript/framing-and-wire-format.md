# Framing & wire format

[Call systems & serialization](../../guide/runtime/call-system.md) covers
the concept; this is the concrete TypeScript API. Both axes are the package's
choice, from `config.idp`'s `wire` key — see
[Wire defaults](../../guide/packages/index.md#wire-defaults).

## Framing

All three framings are implemented and wire-compatible with the Rust runtime:
`Datagram2Framing` (`datagram@2`, the default, for
[connections](connections.md)), `DatagramFraming` (the lockstep `datagram`)
and `JsonRpcFraming`. Which one generated code uses is decided at generation
time: the protocol's `@framing` annotation, else the package's `wire.framing`,
else `datagram@2` — exactly as on the
[Rust page](../rust/framing-and-wire-format.md).

A lockstep `<Proto>Client` / `serve<Proto>` takes an optional `framing`
argument if you want to override it when wiring a `Client` / `Server` by hand:

```typescript
import { Client, JsonRpcFraming } from "@comline/runtime";

const client = await Client.connect(transport, codec, IR_HASH, new JsonRpcFraming());
```

## Wire format

The generated code exports the package's format:

```typescript
export const Format: Codec = new PackedCodec();
```

The package's `serve` / `accept` / `connect`, and each lockstep helper, use
it by default; a lockstep helper takes another `Codec` as an optional
argument.

Two codecs ship. Every `Codec` has a `name` (used in the handshake) plus
`encode` / `decode`.

- **`PackedCodec`** (`packed@1`, the default): fixed-width fields with no tags
  or names; see [`packed@1`](../../reference/wire/packed.md). A JS value
  doesn't say whether a number is a `u16` or an `f64`, so the generator emits
  a `Layout` for each type (`MessageLayout`, `ChatSendParamsLayout`, ...),
  and every encode and decode in generated code passes it. Calling a codec by
  hand, pass the layout too: `Format.encode(value, MessageLayout)`.
- **`JsonCodec`** (`json@1`).

There's no MessagePack codec for TypeScript yet, so a TypeScript target
can't generate a package whose `wire.format` is `msgpack@1`: `comline build`
and `comline generate` refuse it.

`u64` and `s64` (and `u128` / `s128`) are `bigint` in both codecs.

## Types-only packages

A package with no protocols, only types, still emits a `Layout` per type. It
imports `Layout` with `import type`, which is erased, so its `package.json`
lists `@comline/runtime` as an optional peer dependency rather than a
dependency. Whoever encodes the types has the runtime already.

## Shipped combinations

What the runtime is proven to speak, feature by feature, is on the
[TypeScript reference page](../../reference/languages/typescript.md#runtime).

| Framing | `packed@1` | `json@1` | `msgpack@1` |
|---|---|---|---|
| `datagram@2` | ✅ | ✅ | — no codec yet |
| `datagram` | ✅ | ✅ | — no codec yet |
| `jsonrpc` | — | ✅ | — |

A TypeScript client and a Rust server (or vice versa) interoperate on any
row both sides support — the handshake, framings and codecs are
byte-compatible with the Rust runtime by design, cross-checked against
its reference vectors.
