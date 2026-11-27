# Connections

To be able to have multiple protocols running on a socket, know that both ends are talking the same
protocols and that the protocol signatures are correct (through handshake), Comline generates some
code that you can use.

Every protocol runs on a
[connection](../../guides/idl/protocol.md#calls-in-both-directions) unless it
picks the lockstep `datagram` framing, in which case it gets a
[client and server](client-and-server.md) instead. This page is the default
case in [What you use](index.md#what-you-use), and uses this schema:

```ids title="snippet.ids"
protocol Chat {
    function send(n: u32) -> u32;
}

@provider = Client
protocol Events {
    function shown(n: u32) -> bool;
    function ping();
}
```

## Serving every protocol

The package gets one `serve`, with a `Services` struct holding a field per
protocol the server provides. Written as a struct literal, every field is
there, so leaving one out doesn't compile; to
[provide only some](#serving-a-subset), say so.

### When they're generated

Snippets like `Services`, `ClientServices`, `accept`, `serve` and `connect` are
generated when the package has one connection to serve, and left out otherwise.

They **aren't generated** when:

- **No protocol is on a connection.** That includes a package with no
  protocols at all. A protocol is on a connection when it uses `datagram@3`
  (the default) or `datagram@2`, or when the client provides it (`@provider = Client` or
  `Multiple`). A server-only protocol on `datagram@1` isn't, so a package of
  only those has no `serve`. The same goes for JSON-RPC protocols, which count
  only once one JSON-RPC protocol in the package is client-provided; then they
  all do.
- **The protocols on connections disagree** on the framing or the handshake.
  No one connection carries them all, and `comline generation` warns, naming
  both protocols. Each protocol still gets its own dispatcher and sender.
- **Only protocols from an external `std` are on a connection.** Only what
  the crate emits counts.

When a package declares protocols but none is on a connection,
`comline generation` says so, and why.

### Using them

They're at the crate root in `lib` mode, and in `connection.rs` beside the
schema files in `code` mode, so the path depends on where you mounted the
generated files. Mounted as the crate's own modules it's `crate::connection`;
under `mod generated;` it's `generated::connection`.

??? note "Using the generated code"

    ```rust
    // `lib` mode
    use my_package::{connect, serve, ClientServices, Services};
    use my_package::snippet::ChatSender;

    // `code` mode, with the generated files as the crate's modules
    // use crate::connection::{connect, serve, ClientServices, Services};
    // use crate::snippet::ChatSender;

    // The side that accepts: handshake, provide every protocol, serve until
    // the peer leaves.
    serve(transport, Services { chat: ChatImpl })?;

    // The side that dials: handshake, provide the client's protocols, and call
    // the server's through their senders.
    let mut conn = connect(transport, ClientServices { events: EventsImpl::default() })?;
    let sent = ChatSender::new(&mut conn).send(3)?;
    ```

    - **`accept(transport, Services { .. })`** is `serve` without the serving: it
      returns the connection, for a server that calls the client first or serves
      one request at a time.
    - **`ClientServices`** holds the protocols the dialling side provides
      (`@provider = Client` or `Multiple`). With none, there is no `ClientServices`
      and `connect` takes only the transport.
    - **A subset** of either is [`Services::new().with_chat(..)`](#serving-a-subset),
      or the literal with `Absent` in the fields left out.
    - **Field names** are the protocol's name in snake case
      (`CharacterInventory` is `character_inventory`). Where two schemas declare
      a protocol of the same name, both are prefixed with their namespace.
    - **The format** is the package's `Format`
      ([Framing & wire format](framing-and-wire-format.md)), and the framing and
      handshake are the protocols'. When the protocols on connections disagree
      on either, no one connection carries them all, so these functions aren't
      generated and `comline generation` warns why.
    - **A schema named `connection`** can't be used in `code` mode, since the
      file would overwrite it.

## Serving a subset

A side doesn't have to provide every protocol of its direction. Say `snippet.ids` also
declares `protocol Admin { function kick(user: u32); }`, which the server provides, and a
public server wants to serve `Chat` and nothing else. Each field of `Services` and `ClientServices` is a
protocol's implementation, or `Absent` for one left out:

```rust
// Every protocol provided: the literal, as before.
serve(transport, Services { chat: ChatImpl, admin: AdminImpl })?;

// A subset: the same literal with `Absent` in the fields left out...
serve(transport, Services { chat: ChatImpl, admin: Absent })?;

// ...or start from nothing and add each protocol.
serve(transport, Services::new().with_chat(ChatImpl))?;

// The dialling side the same way.
let mut conn = connect(transport, ClientServices::new().with_events(EventsImpl::default()))?;
```

`Services::new()` provides nothing, and each `with_<field>` provides one more
(`with_chat`, `with_admin`). An implementation that doesn't implement the
protocol's trait is still a compile error naming it. `accept` and `async = true`
take a subset the same way.

A connection carries exactly what its Hello lists
([`comline@2`](../../reference/wire/handshakes/comline@2.md#what-an-ends-hello-lists)):

- **What the Hello lists.** Each end lists the protocols it provides, and every
  protocol of the other side, which it calls: the server lists what `Services`
  holds and every client-provided protocol, the dialling side what
  `ClientServices` holds and every server-provided one. A protocol both provide
  (`@provider = Multiple`) is listed once. The peer refuses a listed protocol it
  doesn't have (`unknown_protocol`), and a protocol an end leaves out of its Hello
  is not on the connection. Two ends that list different protocols still connect.
- **A refused protocol is skipped, not an error.** `accept` and `connect` provide
  only the protocols the handshake accepted. If a client written before `Admin`
  existed lists `Chat` alone, the server's `Admin` is refused, the connection
  still comes up, and `Chat` is served.
- **A call outside the connection fails locally.** A sender's call to a protocol
  the handshake didn't accept returns `RuntimeError::Unavailable` and writes
  nothing. `unavailable(&mut conn)` says which function, and why the peer refused
  its protocol (`Reason::UnknownProtocol` for one it didn't list).
- **Wired by hand,** `provide_on` returns a `Result` and fails with `Unavailable`
  for a protocol the handshake didn't accept ([by hand](#by-hand)).

With `comline@1`, `none` or JSON-RPC there is no Hello, so a subset means only
fewer dispatchers: nothing is negotiated and nothing is refused.

## What codegen emits

The entry points are in `connection.rs`, and open with a header that says, for
this package's protocols, what to implement, serve, dial and call:

```rust
// Generated by Comline
// For Rust 1.85.0 or later; verified up to 1.99.
//! The package's protocols share one connection: `datagram@3` framing, the `comline@2` handshake. To use it:
//!
//! - Implement the trait of each protocol the server provides: `snippet::Chat`.
//! - Implement the trait of each protocol the client provides: `snippet::Events`.
//! - Serve with [`serve`]`(transport, Services { chat: .. })`, which serves every call until the peer leaves. [`accept`] hands the connection back first, for a server that calls the client or serves one call at a time.
//! - Dial with [`connect`]`(transport, ClientServices { events: .. })`.
//! - To provide only some of a side's protocols, start from `Services::new().with_chat(..)` or `ClientServices::new().with_events(..)` and add each with its `with_` method, or write [`Absent`] in the fields left out. The `comline@2` Hello then lists what is provided and every protocol of the other side this end calls, and a protocol it doesn't list isn't on the connection.
//! - Call the server from the dialling side: `ChatSender::new(&mut conn).send(..)`.
//! - Call the client from the accepting side, on the connection [`accept`] returns or the peer a handler is given: `EventsSender::new(&mut conn).shown(..)`.
//!
//! [`Connection<T>`](Connection) names the connection over a transport `T`, written `Connection<Tcp>`; [`Format`] is the package's wire format.

/// The package's wire format (`wire.format`).
pub type Format = comline_runtime::format::Packed;

/// Digest of every schema in the package — what a connection's handshake
/// checks, so both ends agree on each protocol's number.
pub const CONNECTION_IR_HASH: u64 = 0x4d934c4e06a6f038;

/// The framing the package's connection runs on (`datagram@3`).
pub type Framing = comline_runtime::contract::Datagram3Framing;

/// The package's connection over the transport `T`: what [`accept`] and [`connect`]
/// return, written `Connection<Tcp>`: [`Format`] over [`Framing`].
pub type Connection<T> = comline_runtime::connection::Connection<T, Format, Framing>;

/// A protocol left out of [`Services`] or [`ClientServices`]: it isn't provided,
/// and the `comline@2` Hello doesn't list it unless this end calls it.
pub struct Absent;

/// What the accepting side provides: one field per protocol. Every field is a
/// protocol's implementation, or [`Absent`] to leave the protocol out;
/// `Services::new()` has them all absent, and `with_<field>` provides one.
pub struct Services<Chat> {
    pub chat: Chat,
}

impl Services<Absent> { pub fn new() -> Self { /* … */ } }

impl<Chat> Services<Chat> {
    pub fn with_chat<P: crate::snippet::Chat + 'static>(self, provider: P) -> Services<P> { /* … */ }
}

// ClientServices<Events>, the same for the protocols the dialling side provides.

pub fn accept<T: Transport, Chat: ProvideSnippetChat>(transport: T, services: Services<Chat>) -> Result<Connection<T>, RuntimeError> { /* … */ }

pub fn serve<T: Transport, Chat: ProvideSnippetChat>(transport: T, services: Services<Chat>) -> Result<(), RuntimeError> {
    accept(transport, services)?.serve()
}

pub fn connect<T: Transport, Events: ProvideSnippetEvents>(transport: T, services: ClientServices<Events>) -> Result<Connection<T>, RuntimeError> { /* … */ }

// Also here, for the `comline@2` handshake: `negotiated`, `warnings` and
// `unavailable`, which read what it agreed, and `#[doc(hidden)]` `HEADER`
// (the Hello up to its protocols), a `P_<PATH>` entry for each protocol (here
// `P_SNIPPET_CHAT`) and `handshake(provided, called)`. `ProvideSnippetChat`
// is the hidden trait `Services` bounds a field by: implemented for `Absent`, and
// for whatever implements `Chat`.
```

Each protocol's file has its trait, its sender, and the plumbing:

```rust
// snippet.rs
pub const IR_HASH: u64 = 0x4d934c4e06a6f038;

#[doc(hidden)]
pub use crate::connection::{CONNECTION_IR_HASH, Format};

#[doc(hidden)]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChatSendParams {
    pub n: u32,
}

pub trait Chat {
    fn send(&self, peer: &mut impl Peer, n: u32) -> Result<u32, Fault<ChatSendError>>;
}

#[doc(hidden)]
pub const CHAT_CALLS: &[&str] = &["send"];

#[doc(hidden)]
pub struct ChatDispatcher<S>(pub S);

impl<S: Chat> ChatDispatcher<S> {
    #[doc(hidden)]
    pub const PROTOCOL: ProtocolNumber = 0;

    /// Fails with `RuntimeError::Unavailable` when the connection ran a `comline@2`
    /// handshake that didn't accept this protocol: the Hello didn't list it, or the
    /// peer refused it. A connection opened without one accepts it.
    pub fn provide_on<T: Transport, W: WireFormat, F: ConnectionFraming>(self, conn: &mut Connection<T, W, F>) -> Result<(), RuntimeError>
    where S: 'static { conn.provide(Self::PROTOCOL, self) }
}

/// Calls protocol `Chat` on the other end of a connection: the peer a
/// `Connection` reaches, or the one a handler was given.
pub struct ChatSender<'p, P: Peer>(pub &'p mut P);

impl<'p, P: Peer> ChatSender<'p, P> {
    pub fn new(peer: &'p mut P) -> Self { /* … */ }

    pub fn send(&mut self, n: u32) -> Result<u32, CallError<ChatSendError>> {
        crate::connection::check_call(&mut *self.0, Self::PROTOCOL, 0, "snippet::Chat", "send")?;
        let (reply, fmt) = self.0.call(Self::PROTOCOL, Call::new(0, "send"), &ChatSendParams { n })?;
        // …
    }
}

// Events, EventsDispatcher (PROTOCOL = 1) and EventsSender, the same way;
// `ping` is one-way, so `EventsSender::ping` returns `Result<(), RuntimeError>`.
```

`Format` and `CONNECTION_IR_HASH` are defined once, in `connection.rs`; each
protocol file re-exports them. The plumbing is `pub`, so you can wire a
connection [by hand](#by-hand), and `#[doc(hidden)]`, so it isn't in rustdoc:
the `…Params` structs, the `…_CALLS` tables, the dispatchers (`Services` provides
them on the connection, so you don't name one) and their `PROTOCOL` numbers.
What rustdoc shows is the traits, the senders, `Services`, `ClientServices`,
`Absent`, `accept`, `serve`, `connect`, `Connection<T>` and `Format`. With
`datagram@2` and `comline@1`, the header is the same, there is no `Framing`, and
`Connection<T>` is `Connection<T, Format>`.

It differs from a client and server in three ways:

- **Handlers take the peer first:** the other end of the connection the call
  came in on. Through it a handler calls back (`EventsSender::new(peer)`),
  reads `peer.id()`, and keeps data on the connection with
  `peer.extensions()`.
- **A sender replaces the client.** `ChatSender` has one method per function,
  as `ChatClient` would, over anything that implements `Peer`: a
  `Connection`, or a handler's peer. Calls return `CallError` as a client's
  do; `@timeout_ms` applies; one-way functions return `Result<(), RuntimeError>`.
- **`CONNECTION_IR_HASH`** covers every schema in the package. It also fixes
  each protocol's number (`ChatDispatcher::PROTOCOL`), its position among the
  package's protocols.

Protocols on `datagram` in the same package keep their `Client` and
`Server`, and so do `jsonrpc` ones unless the package has a JSON-RPC protocol
on a connection (see [Over JSON-RPC](#over-json-rpc)).

## By hand

`serve` is a few lines over the runtime's `Connection`, which is also how to
pick another format for one connection. For the default `datagram@3` and
`comline@2`, the package's `handshake()` is the handshake, and `Datagram3Framing`
the framing:

```rust
use comline_runtime::contract::Datagram3Framing;
use my_package::connection::{handshake, Format, CONNECTION_IR_HASH, P_SNIPPET_CHAT, P_SNIPPET_EVENTS};

// This end provides `Chat` and calls `Events`: its Hello lists those two.
let mut hs = handshake(&[P_SNIPPET_CHAT], &[P_SNIPPET_EVENTS]);
let mut conn = comline_runtime::connection::Connection::accept_with(
    transport, Format::default(), Datagram3Framing, &mut hs, CONNECTION_IR_HASH,
)?;
ChatDispatcher(ChatImpl).provide_on(&mut conn)?;
conn.serve()?;                              // until the transport closes
```

`handshake(provided, called)` builds the Hello from the `P_` entries of the
protocols this end provides and the ones it calls, so a connection wired by
hand lists what you tell it to. `provide_on` returns a `Result`: with
`comline@2` it fails with `RuntimeError::Unavailable` for a protocol the
handshake didn't accept, one this end's Hello didn't list or the peer refused.
The package's `accept` also keeps what `comline@2` agreed in the connection's
extensions, which `negotiated`, `warnings` and `unavailable` read, and each
sender checks before it calls. Opened as above, a connection has nothing to
check against for calls, and every call goes. With no Hello at all
(`comline@1`, `none`), `provide_on` takes any protocol. On `datagram@2` and `comline@1` the
connection is simpler, and `Connection::accept(transport, Format::default(),
CONNECTION_IR_HASH)` is all of it.

`serve_one()` handles a single frame instead, returning `Ok(false)` once the
transport has closed. Between frames, this side can call the client on its
own:

```rust
conn.serve_one()?;
EventsSender::new(&mut conn).shown(7)?;
```

The dialling side is `Connection::connect_with` with the same arguments. While
a call waits for its reply, the connection serves whatever the server sends
first, such as the `Events::shown` call its handler makes. A request to a
protocol this side doesn't provide is answered with a fault.

## Over JSON-RPC

A JSON-RPC protocol the client provides runs on a connection too, and then so
do the package's other JSON-RPC protocols
([the rules](../../guides/idl/protocol.md#json-rpc-on-a-connection)). The
package's `serve` and `connect` open the connection with `JsonRpcFraming` and
the `Json` format, and `connection.rs` names them:

```rust
/// The framing the package's connection runs on (`jsonrpc`).
pub type Framing = comline_runtime::framing::JsonRpcFraming;

/// The package's connection over the transport `T`: what [`accept`] and [`connect`]
/// return, written `Connection<Tcp>`: JSON over [`Framing`].
pub type Connection<T> = comline_runtime::connection::Connection<T, comline_runtime::format::Json, Framing>;
```

By hand, the rest of this page is unchanged:

```rust title="json_connection.rs"
use comline_runtime::format::Json;
use comline_runtime::framing::JsonRpcFraming;
use comline_runtime::handshake::ComlineHandshake;

let mut conn = Connection::accept_with(transport, Json::default(), JsonRpcFraming, &mut ComlineHandshake, CONNECTION_IR_HASH)?;
// The dialling side:
let mut conn = Connection::connect_with(transport, Json::default(), JsonRpcFraming, &mut ComlineHandshake, CONNECTION_IR_HASH)?;
```

An `AsyncConnection` opens with
`AsyncConnection::handshake(transport, Json, JsonRpcFraming, CONNECTION_IR_HASH)`.

- **Each call table holds method names:** `["send"]`, or under
  `method_names = qualified`, `["chat.Events/shown", "chat.Events/ping"]`.
  A request is routed to the provided protocol whose table has its method.
- **A one-way call is a notification,** sent with no `id`. A request without
  one gets no reply, even if its function returns a value.

A JSON-RPC protocol that stays off a connection keeps its `Client` and
`Server`: `RpcDispatcher(MyRpc).serve(&mut transport)` and
`RpcClient::connect(transport)`, which encode JSON.

## Extensions (A handler calling back)

`Extensions` holds one value per type (`insert`, `get`, `get_mut`,
`remove`). It belongs to the connection, so `Sent` counts this client's
messages and no one else's.

```rust title="chat_extensions.rs"
struct Sent(u32);

impl Chat for ChatImpl {
    fn send(&self, peer: &mut impl Peer, n: u32) -> Result<u32, Fault<ChatSendError>> {
        let shown = EventsSender::new(peer).shown(n).map_err(|_| Fault::Internal)?;
        let sent = peer.extensions().get_mut::<Sent>().map(|s| { s.0 += 1; s.0 });
        let sent = sent.unwrap_or_else(|| { peer.extensions().insert(Sent(1)); 1 });
        Ok(sent)
    }
}
```

## Threads

A `Connection` is blocking and does one thing at a time. A request is
handled to the end before the next frame is read, and a call made while
serving finishes before the request that made it. To call the peer from
another task while the connection serves, generate for the async driver.

## Async

With `async = true` in [`comline.toml`](../../reference/package/user-configuration.md#async),
connection protocols are generated for the runtime's `AsyncConnection`
instead, on any executor. `Connection<T>` becomes `AsyncConnection<T, Format>`
(over [`Framing`](#what-codegen-emits), where there is one):

```rust title="generated.rs"
pub trait Chat: Send + Sync + 'static {
    fn send(&self, peer: &impl AsyncPeer, n: u32) -> impl ::core::future::Future<Output = Result<u32, Fault<ChatSendError>>> + Send;
}

#[doc(hidden)]
pub struct ChatAsyncDispatcher<S>(pub S);       // PROTOCOL, provide_on(&mut AsyncConnection)

/// Calls protocol `Chat` on the other end of a connection: the peer an
/// `AsyncConnection`'s handle reaches, or the one a handler was given.
pub struct ChatAsyncSender<'p, P: AsyncPeer>(pub &'p P);
```

A handler is written as an `async fn`, and awaits its calls back:

```rust
impl Chat for ChatImpl {
    async fn send(&self, peer: &impl AsyncPeer, n: u32) -> Result<u32, Fault<ChatSendError>> {
        let shown = EventsAsyncSender::new(peer).shown(n).await.map_err(|_| Fault::Internal)?;
        // …
    }
}
```

The connection is a future the application spawns; its handles call the
peer from any task. The generated crate enables the runtime's `async`
feature; in `code` mode, the file names the feature to add.

The package's `serve`, `accept` and `connect` are `async` too. `accept` and
`connect` return the connection not yet running, so the caller can take a
`handle()` before spawning it:

```rust
let server = tokio::spawn(serve(acceptor, Services { chat: ChatImpl }));

let client = connect(dialler, ClientServices { events: EventsImpl::default() }).await?;
let to_server = client.handle();
tokio::spawn(client.run());

let sent = ChatAsyncSender::new(&to_server).send(3).await?;
```

Requests are handled in order, except while every running handler
waits on a call to the peer: the next one starts, as it may be that call's
nested request. `conn.concurrent(n)` lets several run at once, and
`conn.set_timer(…)` gives `@timeout_ms` a clock. The runtime's `tokio`
feature adds TCP (`async_connection::tokio::Tcp`) and a timer.

Protocols that aren't on a connection keep their blocking `Client` and
`Server` either way.

## Without generated code

`Connection::provide(protocol, dispatcher)` registers any `Dispatch`, and returns a `Result`: `Unavailable` for a protocol the `comline@2` handshake didn't accept. One
that needs the peer implements `Dispatch::dispatch_with`, whose default
calls `dispatch`. `Connection` implements `Peer`, whose `call`, `notify` and
`call_with_timeout` take the protocol number. Underneath, `connection::State`
is the I/O-free core: it encodes requests and replies, and turns frames
into `Event`s (a request, a reply, or a stale reply to an abandoned call).
