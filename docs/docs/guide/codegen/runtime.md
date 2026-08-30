# Runtime libraries

For the [runtime](../runtime/index.md) to handle your schema's messages and
protocol calls, it needs the schema's shape available in a form the language
runtime can load. One way is to compile the generated types directly into your
project. Another — without adding Comline to your build — is to generate a
**standalone library** from the schema and let the runtime load that.

This is what `comline generate`'s `mode` selects:

| `mode` | Output |
|---|---|
| `code` | plain source text you drop into your own tree — the only mode built today |
| `lib` | a buildable library skeleton (e.g. a crate with `Cargo.toml` + `src/`) |
| `dylib` | `lib`, compiled to a dynamic library for a language runtime to load at run time |

`lib` and `dylib` are planned. The open questions around them — how the generated
library is named and versioned, and what identity the runtime checks when it
loads a `dylib` — are worked through in
[Consumer generation configuration](../../design/consumer-generation-config.md).
