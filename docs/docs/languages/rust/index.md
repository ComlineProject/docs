# Rust

Status: shipped. `comline-codegen-rust` generates `code` mode (plain
source files) and `lib` mode (a buildable crate) — see [Library
generation](../../guide/codegen/library-generation.md) for what each mode
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

## The one fact everything else here builds on

The runtime is **sync**, `&mut self`-based, and `no_std`-first. There is
no `Arc`, `Rc`, `Mutex`, or thread spawned anywhere inside it — every call
blocks the caller until the response arrives, by design, so it works the
same on a bare-metal target with no allocator as it does in a normal
`std` binary. The crate's own intent, stated in
`contract/dispatch.rs`, is explicit about this being deliberate for now:

> Sync — no boxed futures on the `no_std` path. An async server layer
> wraps this behind the `std` feature.

That layer doesn't exist yet. Concurrency — running calls on several
threads, or from an async runtime — is entirely something *you* build on
top, not something the runtime hands you. [Sync, async &
concurrency](concurrency.md) covers the patterns.

## Where to go next

- [Client & server](client-and-server.md) — connecting, serving, and the
  shape codegen actually emits.
- [Framing & wire format](framing-and-wire-format.md) — `Json` vs.
  `MsgPack`, `DatagramFraming` vs. `JsonRpcFraming`, and which is a
  build-time choice vs. a runtime one.
- [Sync, async & concurrency](concurrency.md) — using a `Client` from more
  than one thread, or from async code, today.
