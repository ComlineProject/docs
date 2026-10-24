# Client & server

This page assumes a schema like [Protocols](../../guide/idl/protocol.md)'s
`Mail` example has already been generated to Rust:

```ids
protocol Mail {
    @timeout_ms = 1000
    function send_message(message: Message) -> string ! RecipientNotFound;
    function fetch_inbox() -> Message[];
}
```

## What codegen emits

Full details are [Code generation](../../guide/codegen/index.md)'s job, not
this page's — but the shapes below are what the generated file actually
contains, so the rest of this page can refer to them by name:

```rust
pub trait Mail {
    fn send_message(&self, message: Message) -> Result<String, Fault<MailSendMessageError>>;
    fn fetch_inbox(&self) -> Result<Vec<Message>, Fault<MailFetchInboxError>>;
}

pub struct MailDispatcher<S>(pub S);       // implements `comline_runtime::contract::Dispatch`
pub struct MailClient<T, W>(pub Client<T, W>);

pub const IR_HASH: u64 = 0x…;              // schema fingerprint, used in the handshake
```

- `Mail` is the trait your implementation fills in — plain `&self`, a
  `Result`, and one error type per request/response function. Every such
  function gets one, whether or not it declares a `!`: a function with no
  `!` gets a type alias to `core::convert::Infallible`, which says the same
  thing the schema does — it cannot raise. See
  [Error handling](#error-handling-two-layers) for the `Fault` wrapper.
- `MailDispatcher<S>` wraps any `S: Mail` and implements the runtime's
  `Dispatch` trait — the thing a `Server` actually drives.
- `MailClient<T, W>` wraps a `comline_runtime::client::Client<T, W>` and
  gives you one method per function, already returning the right types.

## Transports today

Two [`Transport`](../../guide/runtime/call-system.md) implementations
ship in `comline-runtime`:

| Transport | Use | Notes |
|---|---|---|
| `InMemory` (`transport::duplex()`) | same-process client + server, tests | an mpsc channel pair — no serialization overhead, nothing to connect |
| `Tcp` | real client/server over a network | `Tcp::connect(addr)` on the client side, `Tcp::new(stream)` wrapping a `TcpStream` you already accepted |

There's no Unix-socket or UDP transport yet (UDP is called out as a future
`InMemory`-style datagram medium in the transport module's own docs); if
you need either, you're writing a `Transport` impl yourself for now — it's
two methods, `send` and `recv`.

## Connecting a client

The generated `connect` always runs the
[handshake](../../guide/runtime/call-system.md#handshake) — there's no
"skip it" option from the generated stub:

```rust
use comline_runtime::format::MsgPack;
use comline_runtime::transport::Tcp;

let transport = Tcp::connect("127.0.0.1:7000")?;
let mut client = MailClient::connect(transport, MsgPack)?;

let body = client.send_message("hello".to_string())?;
```

`connect` builds a `Handshake` from `IR_HASH` and the wire format's name,
sends it, reads the peer's, and fails with `RuntimeError::Handshake` if the
schema, wire format, or framing don't match on both ends — before a single
real call goes out.

**The constraint to know about**: a call borrows the client mutably for as
long as you hold onto its response. This isn't a generated-code quirk —
it's `Client::call`'s own signature, and it falls out of the design
directly: the client reuses one send/receive buffer across calls (no
per-call allocation), so the previous response has to be decoded or
dropped before the next call can reuse that buffer. In practice this means
one outstanding call at a time, which also means a `Client` is naturally
single-threaded unless you add your own synchronization — see [Sync, async
& concurrency](concurrency.md).

## Serving

There's no listener/accept loop built into `Server` or the generated
dispatcher — `Server` serves *one* already-connected transport until it
closes. Accepting connections is your loop:

```rust
use std::net::TcpListener;
use std::thread;

use comline_runtime::format::MsgPack;
use comline_runtime::transport::Tcp;

struct MyMail;

impl Mail for MyMail {
    fn send_message(&self, message: Message) -> Result<String, MailSendMessageError> {
        Ok(format!("sent: {}", message.body))
    }
    fn fetch_inbox(&self) -> Result<Vec<Message>, MailFetchInboxError> {
        Ok(vec![])
    }
}

let listener = TcpListener::bind("127.0.0.1:7000")?;
for stream in listener.incoming() {
    let stream = stream?;
    thread::spawn(move || {
        let mut transport = Tcp::new(stream);
        MailDispatcher(MyMail).serve(&mut transport, MsgPack).unwrap();
    });
}
```

`MailDispatcher(MyMail).serve(transport, format)` is the generated
convenience method: it runs the protocol's handshake (`comline@1`
unless the schema says `none`) with the generated `IR_HASH`, then serves
calls until the transport closes. One
thread per connection is the obvious idiom here, not something the
runtime enforces — nothing stops you from `serve_one` in a loop you drive
yourself (an event loop, a single thread multiplexing several
transports) instead.

## Error handling, two layers

The two ends see different shapes, because they can fail in different
ways. Provider-side, your trait methods return `Result<R, Fault<E>>`;
client-side, every generated method returns `Result<R, CallError<E>>`:

```rust
pub enum Fault<E> {          // provider side
    App(E),                  // a schema error, declared with `!`
    Internal,                // a failure the schema does not describe
}

pub enum CallError<E> {      // client side
    App(E),                  // the provider raised a schema error
    Runtime(RuntimeError),   // transport, framing, decode, timeout, fault, …
}
```

`App` is the same thing on both sides: "the call reached the provider and
it said no, here's why, typed." It is the half the schema defines, and `E`
is the generated error type for that function.

`Fault::Internal` is the other half of the provider's story. An
implementation can fail in ways its schema never described — a dead
database, a poisoned lock — and `Internal` is how it says so instead of
panicking inside the dispatcher. Nothing about it crosses the wire: the
caller learns only `RuntimeError::Provider`, because there is no wire
representation for arbitrary provider detail and inventing one would leak
your internals to everyone who calls you. Log the real reason your own
side; return `Fault::Internal`.

That is also why `E` being uninhabited costs you nothing.
`Fault<Infallible>` is still inhabited, so a function declaring no `!` can
still fail — it just cannot fail in a way the *schema* named.

`CallError::Runtime` is everything that isn't the schema's business — a
dropped connection, a decode failure, a `Handshake` mismatch, a
`call_with_timeout` that never got a reply, or the peer's
`Fault::Internal` arriving as `RuntimeError::Provider`. Match on
`CallError::App` the same way you'd match the error enum directly; treat
`Runtime` as the category of failure your retry/reconnect logic cares
about, not something to pattern-match variant by variant.

`?` works on the provider side: `Fault<E>` has `From<E>`, so a helper
returning the schema's own error type threads through without ceremony.

## What a raised error prints

Each generated error struct, and each error enum with variants, gets a
`Display` built from the `message` its `error` declaration requires — so
the sentence you wrote in the schema is what `{}` and `.to_string()`
produce, with `{self.field}` placeholders filled in:

```ids
error NotFound {
    message = f"no entry for {self.key}"
    key: string
}
```

```rust
NotFound { key: "k".into() }.to_string()   // "no entry for k"
```

An error enum delegates to whichever error it holds, so printing
`MailSendMessageError` prints the raised error's own message.

Every generated error, and every error enum, also implements
`core::error::Error`, so it works with `?` into `Box<dyn Error>` and with
error-reporting crates, in `no_std` code too.
