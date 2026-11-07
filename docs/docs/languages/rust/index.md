# Rust

Status: shipped. `comline-codegen-rust` generates `code` mode (plain
source files) and `lib` mode (a buildable crate) — see [Library
generation](../../guides/codegen/library-generation.md) for what each mode
produces. Generated code depends on the **`comline-runtime`** crate
(MPL-2.0 — the piece that actually ships inside your program, as opposed
to the GPL-3.0 generator that only runs at build time).

Not published to crates.io yet. Pin it by git rev, the same way the rest
of the toolchain does (see `cli/Cargo.toml`'s own pattern if you want a
worked example):

```toml
[dependencies]
comline-runtime = { git = "https://github.com/ComlineProject/runtime", rev = "…" }
```

## Sync by default, async when asked

The runtime is `no_std`-first and **sync** by default: a call blocks until
its reply arrives, and nothing inside the runtime spawns a thread or takes a
lock, so it works the same on a bare-metal target with no allocator as in a
normal `std` binary.

Set [`async = true`](../../reference/congregation/comline-toml.md#async) in
`comline.toml` and connection protocols are generated for the runtime's
**async** driver instead: handlers are `async fn`s, the connection is a future
you spawn on any executor, and handles call the peer from any task
([Connections → Async](connections.md#async)). Protocols on the lockstep
`datagram` framing keep their blocking client and server either way.

## Where to go next

- [Client & server](client-and-server.md) — connecting, serving, and the
  shape codegen actually emits.
- [Framing & wire format](framing-and-wire-format.md) — `Packed`, `Json`
  and `MsgPack`; `Datagram2Framing`, `DatagramFraming` and `JsonRpcFraming`;
  and how the package's `wire` key picks both.
- [Connections](connections.md) — the default: every protocol on one
  connection, calls in both directions, sync or async.
- [Sync, async & concurrency](concurrency.md) — sharing a lockstep `Client`
  between threads, and calling it from async code.
