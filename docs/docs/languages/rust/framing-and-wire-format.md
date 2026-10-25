# Framing & wire format

[Call systems & serialization](../../guide/runtime/call-system.md)
introduces these as two independent axes — how a call is framed, and how
its payload is serialized. This page is the concrete Rust API for both.

Both are the package's choice, declared once in `config.idp`:

```idp
wire = { format = "packed@1" framing = "datagram@2" }
```

Those two values are the defaults, so a package that writes nothing gets
them. See [Wire defaults](../../guide/packages/index.md#wire-defaults).

## Framing is a build-time choice

Which framing the generated code uses is decided when the code is generated,
not when it runs. A protocol's own `@framing` wins; otherwise it gets the
package's `wire.framing`, else `datagram@2` — see
[Protocols](../../guide/idl/protocol.md#annotations). The result is baked into
the generated code: there's no framing argument to swap it at the call site.

```ids
@framing = "jsonrpc"
protocol Mail {
    function send_message(message: Message) -> string ! RecipientNotFound;
}
```

Three framings exist:

- **`Datagram2Framing`** (`datagram@2`, the default): every frame says whether
  it's a request or a reply, and which protocol it's for, so protocols run on
  a [connection](connections.md), where either end can call and one transport
  carries them all.
- **`DatagramFraming`** (`datagram`, also spelled `datagram@1`): the lockstep
  framing. A client sends a request and reads the next frame as its reply, one
  protocol per transport. A protocol on it gets a `<Proto>Client` and a
  `<Proto>Dispatcher` with their own `connect` / `serve`
  ([Client & server](client-and-server.md)).
- **`JsonRpcFraming`**: a [JSON-RPC 2.0](https://www.jsonrpc.org/specification)
  wire shape.

They live in `comline_runtime::contract` and `comline_runtime::framing`. If
you're wiring up a lockstep `Client` / `Server` by hand instead of through
generated code, pick one explicitly:

```rust
use comline_runtime::client::Client;
use comline_runtime::format::Json;
use comline_runtime::framing::JsonRpcFraming;

let client = Client::connect_with_framing(transport, Json, JsonRpcFraming, IR_HASH)?;
```

`Client::connect` / `Server::new` default to `DatagramFraming`;
`connect_with_framing` / `with_framing` take any `F: Framing`. The runtime
fills the handshake in from the format's and framing's names; you pass only
the schema's `IR_HASH`.

## The wire format is the package's `Format`

The generated code names the package's format once:

```rust
pub type Format = comline_runtime::format::Packed;
```

The package's `serve` / `accept` / `connect`, and each lockstep protocol's own
`serve` and `connect`, use it, so there's no format argument to pass:

```rust
let client = MailClient::connect(transport)?;
```

A caller that needs another format for one connection has
`serve_with_format` / `connect_with_format`. The peer has to use the same one.

Three formats implement `comline_runtime::contract::WireFormat`:

| Format | Type | Needs | |
|---|---|---|---|
| `packed@1` (default) | `format::Packed` | nothing: `no_std`, no allocator | fixed-width fields, no tags or names; see [`packed@1`](../../reference/wire/packed.md) |
| `json@1` | `format::Json` | `std` | `serde_json`; readable on the wire |
| `msgpack@1` | `format::MsgPack` | `std` | `rmp-serde`, structs encoded positionally |

`packed@1` and `msgpack@1` are positional: a struct is its fields in
declaration order, with no names. That's why the append-only field discipline
schema evolution already requires (see
[Versioning rules](../../reference/versioning.md)) matters just as much for
the wire as for the frozen IR: inserting a field in the middle would silently
desync two ends on different schema versions.

## Both ends must agree

The [handshake](../../guide/runtime/call-system.md#handshake) checks the
schema fingerprint, the wire format's name, and the framing's name — and
refuses the connection on any mismatch, before a real call is attempted.
There's no negotiation; both sides are expected to be built from the same
schema, so they get the same `Format`.

## Shipped combinations

What the runtime is proven to speak, feature by feature, is on the
[Rust reference page](../../reference/languages/rust.md#runtime).

| Framing | `packed@1` | `json@1` | `msgpack@1` |
|---|---|---|---|
| `datagram@2` | ✅ | ✅ | ✅ |
| `datagram` | ✅ | ✅ | ✅ |
| `jsonrpc` | — | ✅ | — |

JSON-RPC's own spec is JSON text, so a package with a JSON-RPC protocol can't
declare another `wire.format`: that's a build error naming the protocol.
Leaving `wire.format` out is fine — the default then applies only to the
package's other protocols.
