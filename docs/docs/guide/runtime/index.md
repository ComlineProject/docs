# Runtime

Transport, message parsing, and routing a [protocol](../idl/protocol.md) call to
its implementation all have to happen at run time. Comline provides a runtime
that does this, so each project does not reinvent it.

## Per-language runtimes

Each language ships its own runtime implementation — not a thin shim
calling into a shared core, but a from-scratch implementation of the same
contract (handshake, framing, wire format), wire-compatible with the
others. The Rust runtime (`comline-runtime`) is the reference; a
TypeScript peer and a Rust peer generated from the same schema negotiate
the same handshake and speak the same request/response bytes, because
each runtime's framing and handshake code is cross-checked against the
others' reference vectors, not because one calls into the other at run
time.

What that means in practice: there is no FFI boundary between a
TypeScript program and a "core" written in Rust. Each runtime is a normal
dependency in its own language, built and shipped like any other
library.

See [Language Guides](../../languages/index.md) for the practical,
per-language next step — spawning a client, serving a protocol, and the
concrete framing/wire-format API. This page stays the conceptual
overview.

## Call system

The pluggable part — the call framing (JSON-RPC, a compact binary format, a
custom one) and the message serialization — is the
[call system](call-system.md).

Generating the schema types the runtime needs is covered in
[Library generation](../codegen/library-generation.md).
