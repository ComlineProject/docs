<!--
---
icon: simple/rust
---
-->

# Rust


## What you use

Which generated items you use depends on the protocol's framing and on who
provides it. The names below are for protocols `Chat` (the server provides it)
and `Events` (the client does), and `Mail` and `Rpc` for the others.

| Case | You implement | To serve | To dial | To call through |
|---|---|---|---|---|
| **The default connection**: every protocol on one [connection](connections.md), `datagram@3` | each protocol's trait: `Chat`, and `Events` for what the client provides. Handlers take the peer first | `serve(transport, Services { chat })`. `accept(transport, Services { chat })` takes the same and hands back the connection first | `connect(transport, ClientServices { events })`, or `connect(transport)` when the client provides nothing | `ChatSender::new(&mut conn)`, on what `connect` returns, what `accept` returns, or the peer a handler is given. With `async = true`, `ChatAsyncSender::new(&conn.handle())` |
| **The lockstep `datagram`**: one protocol per transport ([lockstep](client-and-server.md)) | the protocol's trait: `Mail` | `MailDispatcher(MyMail).serve(&mut transport)` | `MailClient::connect(transport)` | `MailClient`'s methods; it takes `&mut self` |
| **JSON-RPC**, a protocol the client provides | as the default connection | as the default: the package's `serve` opens the connection with `JsonRpcFraming` ([over JSON-RPC](connections.md#over-json-rpc)) | as the default | as the default |
| **JSON-RPC**, a server-only protocol | the protocol's trait: `Rpc` | `RpcDispatcher(MyRpc).serve(&mut transport)` | `RpcClient::connect(transport)`, encoding JSON | `RpcClient`'s methods |
| **By hand** | the same traits | `Connection::accept_with(transport, Format::default(), Datagram3Framing, &mut handshake(), CONNECTION_IR_HASH)?`, then `ChatDispatcher(chat).provide_on(&mut conn)` and `conn.serve()?` ([by hand](connections.md#by-hand)). Lockstep: `Server::new(MailDispatcher(mail), format).serve(transport, IR_HASH)` | `Connection::connect_with(…)`, the same way. Lockstep: `MailClient::connect_with_format(transport, format)` | the same senders and clients |

A package whose protocols disagree on the framing or the handshake has no one
connection, so no `serve` or `connect`; each protocol keeps its own dispatcher
and sender ([when they're generated](connections.md#when-theyre-generated)).

### What's in the generated files

A package with a connection gets `connection.rs` (in `lib` mode, the crate
root). It opens with a `//!` header saying which of the above to use, for this
package's protocols, and holds `Services`, `ClientServices`, `accept`, `serve`
and `connect`, plus three names every protocol file shares:

- **`Format`**, the package's wire format, and **`CONNECTION_IR_HASH`**, the
  digest the handshake checks. They're defined once, here. Each protocol file
  re-exports them as `#[doc(hidden)]`, so by hand `Format` and
  `CONNECTION_IR_HASH` come from `connection.rs`.
- **`Connection<T>`**, the connection over a transport `T` (`Connection<Tcp>`):
  what `accept` and `connect` return.
- **`Framing`**, the framing the connection runs on, named when it isn't the
  runtime's default (`datagram@2`).

The plumbing stays `pub`, so it's there for by-hand use, and is
`#[doc(hidden)]`, so it isn't in `cargo doc`: the `…Params` structs, the
`…_CALLS` tables, the dispatchers of a connection (`ChatDispatcher`, whose
`provide_on` is what `Services` calls), each protocol's `PROTOCOL` number, and
what the `comline@2` handshake is built from (`HELLO`, `handshake()`). What's left in rustdoc is what the header
tells you to use: the traits, the senders, `Services`, `ClientServices`,
`accept`, `serve`, `connect`, `Connection<T>` and `Format`. A lockstep protocol's own
file has no header: in `lib` mode the crate root's docs list it, with the
`…Dispatcher(provider).serve(&mut transport)` and `…Client::connect(transport)?`
to use, and its dispatcher and client are documented as they are.

The pages below show each case as it's generated.

## Adding runtime to dependencies

### From crates.io
Not published to crates.io yet. Pin it by git rev, the same way the rest
of the toolchain does (see `cli/Cargo.toml`'s own pattern if you want a
worked example):


```toml title="Cargo.toml"
[dependencies]
comline-runtime = { git = "https://github.com/ComlineProject/runtime", rev = "…" }
```

### From git

If you are generating a package into code, you can check in the generated
`Cargo.toml` for the exact pin revision and features, which is much easier.


## Where to go next


<div class="grid cards" markdown>

- **[Connections](connections.md)** — the default: every protocol on one
  connection, calls in both directions, sync or async.

- **[Lockstep `datagram`: client & server](client-and-server.md)** — the lockstep
  framing's `<Protocol>Client` and `<Protocol>Dispatcher`, and the shape
  codegen emits for them.

- **[Framing & wire format](framing-and-wire-format.md)** — `Packed`, `Json`
  and `MsgPack`; `Datagram3Framing`, `Datagram2Framing`, `DatagramFraming` and
  `JsonRpcFraming`; and how the package's `wire` key picks both.

- **[Sync, async & concurrency](concurrency.md)** — sharing a lockstep `Client`
  between threads, and calling it from async code.

</div>
