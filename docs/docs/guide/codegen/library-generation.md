# Library generation

[Code generation](index.md) turns a schema into **source text** — the type
definitions and protocol traits. **Library generation** goes further and wraps
that source into a **package**: a manifest (`Cargo.toml`, `pyproject.toml`, a
`.rockspec`), the module layout, and — when the consumer is in another language
— the FFI surface a [runtime](../runtime/index.md) loads and dispatches through.

`comline generate`'s `mode` chooses how far generation goes. It is set per target
in [`comline.toml`](../../reference/congregation/comline-toml.md) (`[generate] mode` or
`[[generate.target]] mode`).

| `mode` | Output | Status |
|---|---|---|
| `code` | bare source files you place in a project yourself | built |
| `lib` | a buildable package (manifest + module tree) | rust, typescript |
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

**rust**: `<out>/rust/` gets a `Cargo.toml` (package name from the
congregation, `serde` dependency), `src/lib.rs`, and `src/<namespace>.rs` per
schema. A nested namespace (`a/b`) becomes a nested module — `src/a.rs`
declaring `pub mod b;` beside `src/a/b.rs`.

**typescript**: `<out>/typescript/` gets a `package.json` (declaring
`@comline/runtime` when any schema has a protocol), a `tsconfig.json`, and
`src/<namespace>.ts` per schema. Each namespace level also gets an `index.ts`
naming its children, so the package's shape mirrors your namespaces:

```
src/index.ts      export * as types from "./types.js";
                  export * as chat from "./chat/index.js";
src/chat/index.ts export * as admin from "./admin.js";
```

Mirroring rather than flattening is what keeps names from colliding: a flat
barrel re-exporting everything into the package root would make two schemas
that both declare a `Request` ambiguous, which TypeScript refuses outright
(TS2308). Both entry styles work:

```ts
import { types } from "my-api";        // types.Greeting
import { Greeting } from "my-api/types";
```

### std is a dependency, not a copy

Comline's standard library is implicitly part of every package, so without
help a `lib` build would vendor `std/http` and `std/validators` into every
generated package. It doesn't:
[`external_std`](../../reference/congregation/comline-toml.md#external_std)
defaults to **on** in `lib` mode, so std's schemas are left out and the
manifest depends on std's own pre-generated package instead —
`comline_std` for rust, `@comline/std` for typescript. Your own nested
namespaces are unaffected; only std is treated this way.

`--no-external-std` (or `external_std = false`) inlines it, which is what
`code` mode does by default since it has no manifest to declare a dependency
in.

One restriction, shared by both generators: a namespace can be a schema or a
parent of deeper schemas, not both. `std.ids` alongside `std/http.ids` leaves
`src/std.rs` (or `export * as std`) with two things to be, so it's refused
with a message naming the pair.

In either language, `<language>/` keeps this target's package from colliding
with another `lib` target sharing the same `out`; a target with `out` to
itself can set
[`flatten = true`](../../reference/congregation/comline-toml.md#flatten) to skip that and
land the package straight into `out`. `layout` plays no part in any of this —
it only applies to `code` mode. Multi-version `lib` output is not done yet.

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

`lib` is built for Rust (see [Language Guides →
Rust](../../languages/rust/index.md) for using the result). `dylib` is
still planned for every language, Rust included. The open questions for
`dylib` — how the generated library is named and versioned, and what
identity the runtime checks when it loads one — are worked through in
[Consumer generation configuration](../../design/consumer-generation-config.md).
The pipeline split (codegen vs libgen vs runtime) and the plan to build these is
in [Generation](../../design/generation.md).
