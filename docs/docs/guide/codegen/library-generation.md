# Library generation

[Code generation](index.md) turns a schema into **source text** — the type
definitions and protocol traits. **Library generation** goes further and wraps
that source into a **package**: a manifest (`Cargo.toml`, `pyproject.toml`, a
`.rockspec`), the module layout, and — when the consumer is in another language
— the FFI surface a [runtime](../runtime/index.md) loads and dispatches through.

`comline generate`'s `mode` chooses how far generation goes. It is set per target
in [`comline.toml`](../../reference/comline-toml.md) (`[generate] mode` or
`[[generate.target]] mode`).

| `mode` | Output | Status |
|---|---|---|
| `code` | bare source files you place in a project yourself | **built today** |
| `lib` | a buildable package (manifest + module tree) | planned |
| `dylib` | `lib`, compiled to a dynamic library a runtime loads at run time | planned |

## `code` — source you wire in yourself

One file per schema namespace (`message.rs`, `user.rs`), containing the structs,
enums and protocol traits. Nothing else — no manifest, no build glue. You add
the module to your project (`mod generated;`) and make sure its dependencies are
present (the rust output opens with `use serde::{Serialize, Deserialize};`, so
the project it lands in must already depend on `serde`).

**Use it when** the schema belongs to *one* project and you just want its types
inside that project:

- the app that speaks the protocol also owns the schema;
- the generated code is checked in / vendored alongside hand-written code;
- you want to control the surrounding build — your `serde` version, your feature
  flags, your module layout.

This is the common case, and the only mode implemented today.

## `lib` — a package other projects depend on

A whole buildable package: the manifest with the right dependencies, a `src/`
module tree, and a top-level module that re-exports every schema. The result is
something you `cargo add` / `pip install` / `luarocks install`, or publish.

**Use it when** the schema is shared:

- one schema package is consumed by several projects, and you want a single
  versioned artifact rather than copies of the source in each;
- you want it installable from the language's package manager;
- the schema and the code that uses it live in different repositories.

## `dylib` — a compiled object a runtime loads

`lib`, then compiled to a `.so` / `.dll` / `.dylib`. A language
[runtime](../runtime/index.md) loads it at run time and dispatches calls through
it; the consuming program never adds Comline — or a Comline build step — to its
own toolchain.

**Use it when** the schema is loaded dynamically:

- a running service picks up schema types without being rebuilt;
- the consumer is in a language with no native Comline generator, but there is a
  runtime for it;
- you want to swap schema versions without recompiling the host.

## Status

`lib` and `dylib` are planned. The open questions — how the generated library is
named and versioned, and what identity the runtime checks when it loads a
`dylib` — are worked through in
[Consumer generation configuration](../../design/consumer-generation-config.md).
The pipeline split (codegen vs libgen vs runtime) and the plan to build these is
in [Generation](../../design/generation.md).
