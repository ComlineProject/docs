# Sync, async & concurrency

The runtime itself makes no decision here — as [the overview
page](index.md) covers, it's plain sync Rust, no threads, no `Arc`
anywhere inside it. Everything below is a pattern for *your* code, not a
feature of `comline-runtime`.

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

let client = Arc::new(Mutex::new(MailClient::connect(transport, MsgPack)?));

let c = Arc::clone(&client);
thread::spawn(move || {
    let body = c.lock().unwrap().send_message("from thread 2".into()).unwrap();
});
```

This isn't just "the safe option because the borrow checker demands it" —
it's a reasonable fit for what's actually happening underneath. [One call
is outstanding at a time](client-and-server.md#connecting-a-client) on
any single `Client` regardless of locking, since a call borrows the
client until its response is consumed. The mutex isn't adding an
artificial bottleneck on top of a runtime that could otherwise pipeline
several calls at once — there's nothing to pipeline yet either way.

If you need actual concurrent calls in flight, that means several
connections (several `Client`s, each with its own transport), not several
threads contending for one.

## Calling from async code

There's no async client or server today — the crate's own stated
intent (quoted on [the overview page](index.md)) is an async layer
wrapping the sync core behind the `std` feature, later. Until that ships,
calling a sync `Client` from inside an async task means not blocking the
reactor:

```rust
let client = Arc::new(Mutex::new(client));

let c = Arc::clone(&client);
let body = tokio::task::spawn_blocking(move || {
    c.lock().unwrap().send_message("hi".into())
})
.await
.unwrap()?;
```

`spawn_blocking` (or your executor's equivalent — `async-std`'s
`spawn_blocking`, a dedicated thread pool) runs the blocking call on a
thread meant for blocking work, so it doesn't stall the async runtime's
other tasks while it waits on the network. Treat this as the bridge until
an async layer exists, not a permanent design — don't build deep
abstractions on top of `spawn_blocking` that you'll need to unwind later.

## Serving several connections concurrently

Covered from the server side in [Client &
server](client-and-server.md#serving): one thread per accepted connection
is the straightforward version, each with its own `Dispatcher` (or a
shared, `Sync` implementation type if your provider logic itself needs
shared state — ordinary Rust at that point, nothing runtime-specific).
