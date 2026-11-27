# Code generation

Once a schema is compiled to its [Intermediate Representation](../ir/index.md),
Comline can emit equivalent source code for a target language: the type
definitions for [structures](../idl/structure.md) and [enums](../idl/enum.md),
and an interface per [protocol](../idl/protocol.md). Because generation works from
the IR, it can target [several languages](../../design/codegen-by-language.md) and
[several past versions](../../design/multi-version-generation.md) of the same
schema.

## What Comline aims for

test

## Using it

`comline generation` is the command; [Generating code](generating-code.md) is the
full guide, and [`comline.toml`](../../reference/package/user-configuration.md) is where a
consumer sets the output location, layout and mode.

Today there are `rust` and `typescript` generators, and both do `code` and
`lib` mode. [Library generation](library-generation.md) covers the modes and
`dylib`, which is still planned.
