# Code generation

Once a schema is compiled to its [Intermediate Representation](../ir/index.md),
Comline can emit equivalent source code for a target language: the type
definitions for [structures](../idl/structure.md) and [enums](../idl/enum.md),
and an interface per [protocol](../idl/protocol.md). Because generation works from
the IR, it can target [several languages](../../design/codegen-by-language.md) and
[several past versions](../../design/multi-version-generation.md) of the same
schema.

## What Comline aims for

Many schema libraries generate just enough to move bytes — message types, and a
thin service stub. Comline tries to carry more of the schema's information into
the generated code: language-specific typing, the protocol surface as a real
interface or trait so editors can complete and check against it, and enough
detail that the generated code is pleasant to use directly rather than only as a
"try it out" artifact.

## Using it

`comline generate` is the command; [Generating code](generating-code.md) is the
full guide, and [`comline.toml`](../../reference/comline-toml.md) is where a
consumer sets the output location, layout and mode.

Today `rust` is the only implemented generator and `code` (plain source text) the
only mode. [Runtime libraries](runtime.md) covers the planned `lib` / `dylib`
modes.
