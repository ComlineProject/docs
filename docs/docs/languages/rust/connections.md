# Connections

A protocol on `datagram@2`, or one the client provides, runs on a
[connection](../../guide/idl/protocol.md#calls-in-both-directions) instead of
a [client and server](client-and-server.md). This page uses this schema:

```ids
@framing = "datagram@2"
protocol Chat {
    function send(text: string) -> u64;
    function count() -> u64;
}

@provider = Client
@framing = "datagram@2"
protocol Events {
    function message(text: string) -> bool;
    function ping();
}
```

## What codegen emits

```rust
pub trait Chat {
    fn send(&self, peer: &mut impl Peer, text: &str) -> Result<u64, Fault<ChatSendError>>;
    fn count(&self, peer: &mut impl Peer) -> Result<u64, Fault<ChatCountError>>;
}

pub struct ChatDispatcher<S>(pub S);       // PROTOCOL, provide_on(&mut Connection)
pub struct ChatSender<'p, P: Peer>(pub &'p mut P);

pub trait Events { /* the same shape */ }
pub struct EventsDispatcher<S>(pub S);
pub struct EventsSender<'p, P: Peer>(pub &'p mut P);

pub const CONNECTION_IR_HASH: u64 = 0x…;   // checked by the handshake
```

It differs from a client and server in three ways:

- **Handlers take the peer first:** the other end of the connection the call
  came in on. Through it a handler calls back (`EventsSender::new(peer)`),
  reads `peer.id()`, and keeps data on the connection with
  `peer.extensions()`.
- **A sender replaces the client.** `ChatSender` has one method per function,
  as `ChatClient` would, over anything that implements `Peer`: a
  `Connection`, or a handler's peer. Calls return `CallError` as a client's
  do; `@timeout_ms` applies; one-way functions return `Result<(), RuntimeError>`.
- **`CONNECTION_IR_HASH`** covers every schema in the package, so it's the
  same in every generated file. It also fixes each protocol's number
  (`ChatDispatcher::PROTOCOL`), its position among the package's protocols.

Protocols on `datagram` or `jsonrpc` in the same package keep their
`Client` and `Server`.

## The side that accepts

```rust
use comline_runtime::connection::Connection;
use comline_runtime::format::Json;

let mut conn = Connection::accept(transport, Json, CONNECTION_IR_HASH)?;
ChatDispatcher(ChatImpl).provide_on(&mut conn);
conn.serve()?;                              // until the transport closes
```

`serve_one()` handles a single frame instead, returning `Ok(false)` once the
transport has closed. Between frames, this side can call the client on its
own:

```rust
conn.serve_one()?;
EventsSender::new(&mut conn).message("pushed")?;
```

## The side that dials

```rust
let mut conn = Connection::connect(transport, Json, CONNECTION_IR_HASH)?;
EventsDispatcher(EventsImpl::default()).provide_on(&mut conn);

let mut chat = ChatSender::new(&mut conn);
let sent = chat.send("hi")?;
```

While `send` waits for its reply, the connection serves whatever the server
sends first, such as the `Events::message` call its handler makes. A request
to a protocol this side doesn't provide is answered with a fault.

## A handler calling back

```rust
struct Sent(u64);

impl Chat for ChatImpl {
    fn send(&self, peer: &mut impl Peer, text: &str) -> Result<u64, Fault<ChatSendError>> {
        let shown = EventsSender::new(peer).message(text).map_err(|_| Fault::Internal)?;
        let sent = peer.extensions().get_mut::<Sent>().map(|s| { s.0 += 1; s.0 });
        let sent = sent.unwrap_or_else(|| { peer.extensions().insert(Sent(1)); 1 });
        Ok(sent)
    }
    // …
}
```

`Extensions` holds one value per type (`insert`, `get`, `get_mut`,
`remove`). It belongs to the connection, so `Sent` counts this client's
messages and no one else's.

## Threads

A `Connection` is blocking and does one thing at a time. A request is
handled to the end before the next frame is read, and a call made while
serving finishes before the request that made it. To call the peer from
another task while the connection serves, generate for the async driver.

## Async

With `async = true` in [`comline.toml`](../../reference/congregation/comline-toml.md#async),
connection protocols are generated for the runtime's `AsyncConnection`
instead, on any executor:

```rust
pub trait Chat: Send + Sync + 'static {
    fn send(&self, peer: &impl AsyncPeer, text: &str)
        -> impl Future<Output = Result<u64, Fault<ChatSendError>>> + Send;
    // …
}

pub struct ChatAsyncDispatcher<S>(pub S);       // PROTOCOL, provide_on(&mut AsyncConnection)
pub struct ChatAsyncSender<'p, P: AsyncPeer>(pub &'p P);
```

A handler is written as an `async fn`, and awaits its calls back:

```rust
impl Chat for ChatImpl {
    async fn send(&self, peer: &impl AsyncPeer, text: &str) -> Result<u64, Fault<ChatSendError>> {
        let shown = EventsAsyncSender::new(peer).message(text).await.map_err(|_| Fault::Internal)?;
        // …
    }
}
```

The connection is a future the application spawns; its handles call the
peer from any task. The generated crate enables the runtime's `async`
feature; in `code` mode, the file names the feature to add.

```rust
use comline_runtime::async_connection::AsyncConnection;

let (client, server) = tokio::join!(
    AsyncConnection::connect(dialler, Json, CONNECTION_IR_HASH),
    AsyncConnection::accept(acceptor, Json, CONNECTION_IR_HASH),
);
let (mut client, mut server) = (client?, server?);
ChatAsyncDispatcher(ChatImpl).provide_on(&mut server);
EventsAsyncDispatcher(EventsImpl::default()).provide_on(&mut client);

let to_server = client.handle();
tokio::spawn(client.run());
tokio::spawn(server.run());

let sent = ChatAsyncSender::new(&to_server).send("hi").await?;
```

Requests are handled in order, except that while every running handler
waits on a call to the peer, the next one starts: it may be that call's
nested request. `conn.concurrent(n)` lets several run at once, and
`conn.set_timer(…)` gives `@timeout_ms` a clock. The runtime's `tokio`
feature adds TCP (`async_connection::tokio::Tcp`) and a timer.

Protocols that aren't on a connection keep their blocking `Client` and
`Server` either way.

## Without generated code

`Connection::provide(protocol, dispatcher)` registers any `Dispatch`. One
that needs the peer implements `Dispatch::dispatch_with`, whose default
calls `dispatch`. `Connection` implements `Peer`, whose `call`, `notify` and
`call_with_timeout` take the protocol number. Underneath, `connection::State`
is the I/O-free core: it encodes requests and replies, and turns frames
into `Event`s (a request, a reply, or a stale reply to an abandoned call).
