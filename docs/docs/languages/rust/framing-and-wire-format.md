# Framing & wire format

[Call systems & serialization](../../guide/runtime/call-system.md)
introduces these as two independent axes — how a call is framed, and how
its payload is serialized. This page is the concrete Rust API for both.

## Framing is a build-time choice

Which framing the generated client and server use is decided when the
code is generated, not when it runs. It comes from the protocol's
`@framing` annotation, or the package's `default_framing` in
`comline.toml`, resolved in that order by the generator — see
[Protocols](../../guide/idl/protocol.md#protocol-annotations). The result
is baked into the generated `<Proto>Client` / `<Proto>Dispatcher`: there's
no framing argument on `connect` or `serve` to swap it at the call site.

```ids
@framing = "jsonrpc"
protocol Mail {
    function send_message(message: Message) -> str ! RecipientNotFound;
}
```

Two framings exist: the default compact `DatagramFraming`, and
`JsonRpcFraming` for a [JSON-RPC 2.0](https://www.jsonrpc.org/specification)
wire shape. Both live in `comline_runtime::contract` /
`comline_runtime::framing`. If you're wiring up a `Client`/`Server` by
hand instead of through generated code, pick one explicitly:

```rust
use comline_runtime::client::Client;
use comline_runtime::contract::Handshake;
use comline_runtime::format::Json;
use comline_runtime::framing::JsonRpcFraming;

let hs = Handshake::new(IR_HASH, "json", "jsonrpc", 0);
let client = Client::connect_with_framing(transport, Json, JsonRpcFraming, hs)?;
```

`Client::connect` / `Server::new` default to `DatagramFraming`;
`connect_with_framing` / `with_framing` take any `F: Framing`.

## Wire format is a call-site choice

Unlike framing, the serialization format is a runtime value you hand to
`connect` / `serve` — the same generated client works with either:

```rust
use comline_runtime::format::{Json, MsgPack};

let client = MailClient::connect(transport, Json)?;     // verbose, debuggable on the wire
let client = MailClient::connect(transport, MsgPack)?;  // compact, binary
```

Both implement `comline_runtime::contract::WireFormat`. `Json` wraps
`serde_json`; `MsgPack` wraps `rmp-serde` and encodes structs
**positionally** — as an array of fields in declaration order, not a
map of names. That's a deliberate trade for size, and it's why the
append-only field discipline schema evolution already requires (see
[Versioning rules](../../reference/versioning.md)) matters just as much
for the wire as it does for the frozen IR: inserting a field in the
middle would silently desync two ends on different schema versions.

## Both ends must agree

The [handshake](../../guide/runtime/call-system.md#handshake) that
`connect` / `serve_handshaked` run checks the schema fingerprint, the wire
format's name, and the framing's name — and refuses the connection on any
mismatch, before a real call is attempted. There's no negotiation; both
sides are expected to be built from the same schema and configured with
the same format.

## Shipped combinations

| Framing | Wire format | Ships |
|---|---|---|
| `datagram` | `json` | ✅ |
| `datagram` | `msgpack` | ✅ |
| `jsonrpc` | `json` | ✅ |
| `jsonrpc` | `msgpack` | — JSON-RPC's own spec is JSON text |
