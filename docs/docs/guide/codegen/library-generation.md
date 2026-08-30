# Library generation

[Code generation](index.md) emits source text. **Library generation** wraps that
source into something another language can load and call without adding Comline
to its build: a package its ecosystem understands — a crate with `Cargo.toml`, a
Python package, a LuaRocks rock — with the FFI surface and build glue already in
place. The [runtime](../runtime/index.md) then loads that library and dispatches
through it.

`comline generate`'s `mode` selects how far generation goes:

| `mode` | Output |
|---|---|
| `code` | plain source text you drop into your own tree — the only mode built today |
| `lib` | a buildable library skeleton (package manifest + `src/` + FFI wrapper) |
| `dylib` | `lib`, compiled to a dynamic library for a language runtime to load at run time |

`lib` and `dylib` are planned. The open questions around them — how the generated
library is named and versioned, and what identity the runtime checks when it
loads a `dylib` — are worked through in
[Consumer generation configuration](../../design/consumer-generation-config.md).
The pipeline split — codegen vs libgen vs runtime — is set out in
[Generation](../../design/generation.md).
