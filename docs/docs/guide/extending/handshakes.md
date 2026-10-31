# Handshakes

A **handshake** runs on a connection before the first call. Comline's own,
`comline@1`, has each end send a small frame naming its schema fingerprint,
wire format and framing, and refuses the peer if they differ. That is right
when Comline talks to Comline. A peer that speaks its own hello, version
negotiation or authentication needs its own handshake, or none.

## Official handshakes

| Name | Does | Gives up |
|---|---|---|
| `comline@1` (the default) | exchanges and checks schema, format and framing | nothing |
| `none` | sends and checks nothing | schema agreement and encoding agreement |

`none` is the absence of a handshake, so it is not declared anywhere.

## Declare and use one

Declare it like any encoding, as `kind = "handshake"`
([Formats and framings](encodings.md#1-declare-it)). Its profile states what
the handshake establishes (see [Giving up guarantees](#giving-up-guarantees)).
A handshake that checks nothing states nothing:

```json
{ "name": "com.acme.hello@1", "kind": "handshake", "facts": {} }
```

Then pick it in the schema. The protocol's `@handshake` wins, then the
package's `handshake` key in `config.idp`, then `comline@1`:

```ids
@handshake = "com.acme.hello@1"
protocol Gateway { /* ... */ }
```

A namespaced handshake that nothing declares is a build error. Map the name to
a type per language, as for any encoding
([Map it to a type](encodings.md#5-map-it-to-a-type)). Generated code then
passes that type, instead of `ComlineHandshake`, wherever it opens a
connection or serves one.

## What a handshake gets

Both runtimes hand the handshake the transport and what the generated code
knows, as `Facts`:

| Fact | Rust | TypeScript |
|---|---|---|
| fingerprint of the frozen schema | `ir_hash: u64` | `irHash: bigint` |
| the wire format's name | `wire_format: &str` | `wireFormat: string` |
| the framing's name | `framing: &str` | `framing: string` |
| transport capability bits | `capabilities: u32` | `capabilities?: number` |

In Rust, `Facts` is `#[non_exhaustive]`: more facts will be added, so build one
with `Facts::new`.

## Implement it in Rust

Implement `Handshake` for a blocking connection and `AsyncHandshake` for an
`AsyncConnection` (the `async` feature). A type can implement both.

```rust
use comline_runtime::contract::RuntimeError;
use comline_runtime::handshake::{Facts, Handshake};
use comline_runtime::transport::Transport;

pub struct Hello;

impl Handshake for Hello {
    fn name(&self) -> &str {
        "com.acme.hello@1"
    }

    fn initiate<T: Transport>(&mut self, transport: &mut T, _local: &Facts<'_>)
        -> Result<(), RuntimeError>
    {
        transport.send(b"HELLO")?;
        let mut buf = Vec::new();
        transport.recv(&mut buf)?;
        if buf == b"WELCOME" { Ok(()) } else { Err(RuntimeError::Handshake) }
    }

    fn respond<T: Transport>(&mut self, transport: &mut T, _local: &Facts<'_>)
        -> Result<(), RuntimeError>
    {
        let mut buf = Vec::new();
        transport.recv(&mut buf)?;
        if buf != b"HELLO" {
            return Err(RuntimeError::Handshake);
        }
        transport.send(b"WELCOME")
    }
}
```

- **`name`** is the versioned name. It should match the declared name.
- **`initiate`** runs on the consumer's side and **`respond`** on the
  provider's. For a symmetric handshake, make them the same.
- **Refuse** a peer by returning an error, by convention
  `RuntimeError::Handshake`.
- **`AsyncHandshake`** has the same three methods as `async fn`s over an
  `AsyncTransport`, whose frames are `Vec<u8>`. Its futures are `Send`.

By hand, pass it in:

| Call | Side |
|---|---|
| `Client::connect_with(transport, format, framing, &mut handshake, ir_hash)` | consumer |
| `Server::serve_with(&mut transport, &mut handshake, ir_hash)` | provider |
| `Connection::connect_with(transport, format, framing, &mut handshake, ir_hash)` | dial, blocking connection |
| `Connection::accept_with(transport, format, framing, &mut handshake, ir_hash)` | answer, blocking connection |
| `AsyncConnection::connect_with(..)` and `accept_with(..)` | dial and answer, async connection; `.await` them |

## Implement it in TypeScript

A `Handshake` is an interface. Refuse a peer by throwing, by convention
`RuntimeError.handshake()`.

```ts
interface Handshake {
  readonly name: string;
  initiate(transport: Transport, local: Facts): Promise<void>;
  respond(transport: Transport, local: Facts): Promise<void>;
}
```

Pass it as the last argument to `Client.connect`, `Server.serve`,
`Connection.connect` or `Connection.accept`. Each defaults to
`new ComlineHandshake()`.

## Skipping a handshake

Hand-wired code can skip the handshake at the call site with
`Client::new_unverified` and `Server::serve_unverified` (`Client.unverified`
and `serveUnverified` in TypeScript). They are named so that skipping is as
visible there as in a schema. A skip decided at a call site can leave one peer
handshaking and the other not, so a peer that can't take part is better
declared with `@handshake` in the schema.

## Giving up guarantees

A handshake can establish two things between peers:

| Fact | Means |
|---|---|
| `schema_agreement` | both ends were built from compatible schemas (the IR hash is checked) |
| `encoding_agreement` | both ends use the same format and framing (both are checked) |

A profile states each as a JSON boolean, and a fact it leaves out counts as
`false`. This is the official `comline@1` profile, which states both true:

```json
{
  "name": "comline@1",
  "kind": "handshake",
  "facts": {
    "encoding_agreement": {
      "value": true,
      "proven_by": [
        "handshake/check-agree",
        "handshake/check-reject-format",
        "handshake/check-reject-framing"
      ]
    },
    "schema_agreement": {
      "value": true,
      "proven_by": [
        "handshake/check-agree",
        "handshake/check-reject-ir-hash"
      ]
    }
  }
}
```

A fact stated `true` is **proven by vectors**: cases of the decode-only op
`handshake_check`, in the profile's `.vectors.json`. One case is a peer that
agrees, which the handshake accepts. For each thing the fact covers there is
a peer frame that differs in only that, which it refuses: the IR hash for
`schema_agreement`, the format and the framing for `encoding_agreement`. See
the [`handshake_check` op](../../reference/conformance.md#ops). A fact stated
`false` claims nothing, so it names no cases.

A protocol **gives up every agreement its handshake's profile doesn't
establish**:

| Handshake | Gives up |
|---|---|
| `comline@1` | nothing |
| `none` | schema agreement and encoding agreement |
| a custom handshake | each fact its profile leaves out or states `false` |

So a custom handshake that states both facts needs no marker, and one that
states only `encoding_agreement` gives up schema agreement. The usual
[`@unverified` rules](../idl/protocol.md#giving-up-a-guarantee) apply: a
missing marker is a build error, a needless one is a warning, and a consumer
accepts the given-up set with `accept_unverified`. Core reads the facts from
the declaration, whether the package or one of its dependencies declares it.
Build output names the cause, for example:

```
gives up schema agreement (handshake `com.acme.hello@1` doesn't establish it)
```

For a handshake that states nothing, the `@unverified` marker is your word
that something else covers both.

```ids
@handshake = "com.acme.hello@1"
@unverified = "the gateway checks the schema itself in its HELLO reply"
protocol Gateway { /* ... */ }
```
