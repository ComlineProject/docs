# Sync, async & concurrency

For [connections](connections.md), the default, concurrency is the runtime's
job: generate with [`async = true`](connections.md#async) and handlers run as
`async fn`s on your executor, with several calls in flight on one connection.
The blocking `Connection` handles one thing at a time
([Threads](connections.md#threads)).

This page is about the lockstep `Client` and `Server` that a protocol on the
`datagram` framing gets. They're plain sync Rust, with no threads and no `Arc`
inside, so everything below is a pattern for *your* code, not a feature of
`comline-runtime`.

## Sync by default, async when asked

The runtime is `no_std`-first and **sync** by default: a call blocks until
its reply arrives, and nothing inside the runtime spawns a thread or takes a
lock, so it works the same on a bare-metal target with no allocator as in a
normal `std` binary.

Set [`async = true`](../../reference/package/user-configuration.md#async) in
`comline.toml` and connection protocols are generated for the runtime's
**async** driver instead: handlers are `async fn`s, the connection is a future
you spawn on any executor, and handles call the peer from any task
([Connections → Async](connections.md#async)). Protocols on the lockstep
`datagram` framing keep their blocking client and server either way.

## Plain sync — the common case

Most of what's shown elsewhere in this guide is already this: own a
`Client` (or a `Dispatcher`) directly, call it, block, move on. If your
program is single-threaded, or each thread owns its own connection (the
[per-connection-thread pattern](client-and-server.md#serving) on the
server side), there's nothing further to do.

## Sharing a `Client` across threads

`Client::call` takes `&mut self`, so sharing one `Client` across threads
needs a lock:

```rust
use std::sync::{Arc, Mutex};

let client = Arc::new(Mutex::new(MailClient::connect(transport)?));

let c = Arc::clone(&client);
thread::spawn(move || {
    let body = c.lock().unwrap().send_message("from thread 2".into()).unwrap();
});
```

The lock costs nothing the lockstep framing wasn't already costing: [one call
is outstanding at a time](client-and-server.md#connecting-a-client) on any
single `Client`, since a call borrows the client until its response is
consumed, and the framing matches a reply to whatever request came before it.

For several calls in flight, use a [connection](connections.md#async), which
matches replies by request id, or several `Client`s, each with its own
transport.

## Calling from async code

The lockstep `Client` has no async form. If you can, move the protocol to a
connection (drop `@framing = "datagram"`) and generate with `async = true`.
Otherwise, call the sync `Client` without blocking the reactor:

```rust
let client = Arc::new(Mutex::new(client));

let c = Arc::clone(&client);
let body = tokio::task::spawn_blocking(move || {
    c.lock().unwrap().send_message("hi".into())
})
.await
.unwrap()?;
```

`spawn_blocking` (or your executor's equivalent) runs the blocking call on a
thread meant for blocking work, so it doesn't stall the async runtime's other
tasks while it waits on the network.

## Serving several connections concurrently

Covered from the server side in [Client &
server](client-and-server.md#serving): one thread per accepted connection
is the straightforward version, each with its own `Dispatcher` (or a
shared, `Sync` implementation type if your provider logic itself needs
shared state — ordinary Rust at that point, nothing runtime-specific).
