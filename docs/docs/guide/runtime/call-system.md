# Call systems & serialization

!!! note "Planned"
    Described here at a high level; the concrete API and the set of built-in
    adapters are still being designed.

The **call system** (sometimes *CaSy*) is the part of the [runtime](index.md)
that turns an invocation of a [protocol](../idl/protocol.md) function into bytes
on a transport and back again.

It is pluggable along two axes:

- **Call format** — how a request/response is framed. A spec like
  [JSON-RPC](https://www.jsonrpc.org/) can be used directly, or a compact binary
  framing, or a custom one.
- **Message serialization** — how the [structures](../idl/structure.md) carried
  by a call are encoded: JSON, [MessagePack](https://msgpack.org/), another
  schema library's format, and so on.

The runtime handles routing between a caller and the protocol implementation; you
pick the formats that fit your deployment.
