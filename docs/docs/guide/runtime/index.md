# Runtime

Transport, message parsing, and routing a [protocol](../idl/protocol.md) call to
its implementation all have to happen at run time. Comline provides a runtime
that does this, so each project does not reinvent it.

## Core runtime

A **core runtime**, written in Rust, provides the base facilities every feature
builds on.

## Per-language runtimes

Languages differ — AOT-compiled, JIT-compiled, interpreted — so each has its own
thin runtime that speaks to the core runtime. If you use C++, the Comline C++
runtime talks to the core and the core talks back, so the pieces work together
for the language you are in. The intent is that integration is seamless from the
user's side.

## Call system

The pluggable part — the call framing (JSON-RPC, a compact binary format, a
custom one) and the message serialization — is the
[call system](call-system.md).

Generating the schema types the runtime needs is covered in
[Library generation](../codegen/library-generation.md).
