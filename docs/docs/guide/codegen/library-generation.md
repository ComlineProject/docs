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
| `code` | bare source files you place in a project yourself | built |
| `lib` | a buildable package (manifest + module tree) | **rust only** |
| `dylib` | a package built with a **stable ABI** and compiled to a dynamic library any language's runtime can load | planned |

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

This is the common case, and where every language generator starts.

## `lib` — a package other projects depend on

A whole buildable package: the manifest with the right dependencies, a `src/`
module tree, and a top-level module listing every schema. The result is
something you `cargo add` / `pip install` / `luarocks install`, or publish.

Implemented for **rust**: `<out>/rust/` gets a `Cargo.toml` (package name from
the congregation, `serde` dependency), `src/lib.rs`, and `src/<namespace>.rs` per
schema. Other languages, multi-version `lib` output, and a schema whose namespace
is nested (`a/b`) are not done yet.

**Use it when** the schema is shared:

- one schema package is consumed by several projects, and you want a single
  versioned artifact rather than copies of the source in each;
- you want it installable from the language's package manager;
- the schema and the code that uses it live in different repositories.

## `dylib` — one compiled object, loadable from any language

The package is built with a **stable ABI** — a C-compatible / `abi_stable`
surface, not Rust's own unstable one — and then compiled to a `.so` / `.dll` /
`.dylib`. A plain compiled crate can only be called from the language it was
written in; a stable-ABI object can be `dlopen`ed and called by anything.

The Comline [runtime](../runtime/index.md) for the consumer's language loads the
object at run time and dispatches through that ABI. The schema's types and
protocol surface become usable **without a code generator for that language** —
only a runtime is required. On load, the runtime checks which schema and version
the object carries.

**Use it when** the schema is consumed across languages or loaded dynamically:

- the consumer's language has a Comline runtime but no code generator — the
  `dylib`, generated once (e.g. from Rust), serves it and every other language
  the same way;
- a running host loads schema types, or swaps schema versions, without being
  rebuilt.

## Status

`lib` and `dylib` are planned. The open questions — how the generated library is
named and versioned, and what identity the runtime checks when it loads a
`dylib` — are worked through in
[Consumer generation configuration](../../design/consumer-generation-config.md).
The pipeline split (codegen vs libgen vs runtime) and the plan to build these is
in [Generation](../../design/generation.md).
