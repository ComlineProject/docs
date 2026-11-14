# Rust

Status: shipped. `comline-codegen-rust` generates `code` mode (plain
source files) and `lib` mode (a buildable crate) — see [Library
generation](../../guides/codegen/library-generation.md) for what each mode
produces.

## Adding runtime to dependencies

Not published to crates.io yet. Pin it by git rev, the same way the rest
of the toolchain does (see `cli/Cargo.toml`'s own pattern if you want a
worked example):

```toml
[dependencies]
comline-runtime = { git = "https://github.com/ComlineProject/runtime", rev = "…" }
```

## Licensing

Generated code depends on the **`comline-runtime`** crate
(MPL-2.0 — the piece that actually ships inside your program, as opposed
to the GPL-3.0 generator that only runs at build time).

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
