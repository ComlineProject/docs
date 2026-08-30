# Overview

Comline takes a schema you write by hand and carries it through a fixed pipeline:

**parse → resolve imports → validate → freeze → generate**

Each stage has its own page in this guide; this is the map.

## 1. Write a schema — [IDL](idl/index.md)

A project is a directory with a package manifest (`config.idp`) and one or more
`.ids` schema files under `src/`. The schema language defines
[structures](idl/structure.md), [enums](idl/enum.md), [protocols](idl/protocol.md),
errors and [settings](idl/settings.md), with [docstrings](idl/docstrings.md)
attached to any of them.

```
comline new my-api      # scaffold config.idp + comline.toml + src/main.ids
```

## 2. Compile to the [Intermediate Representation](ir/index.md)

`comline check` parses, resolves imports and validates. `comline build` does that
and then **freezes** the result: the schema becomes a set of immutable IR units
written into a content-addressable store, [`.comline/`](ir/cas.md), as a new
commit in an append-only chain.

The package version bumps automatically on each build, by the largest change
since the last one — see [Versioning rules](../reference/versioning.md).

## 3. [Generate code](codegen/generating-code.md)

`comline generate` turns the compiled schema into source for a target language.
*What* languages a package supports is declared in `config.idp`; *where* the code
lands and in what layout is the consumer's choice, in
[`comline.toml`](../reference/comline-toml.md). One schema history can be
generated across [several languages](../design/codegen-by-language.md) and
[several past versions](../design/multi-version-generation.md) at once.

## 4. [Runtime](runtime/index.md)

At run time a runtime library handles transport, message parsing and routing a
[protocol](idl/protocol.md) call to its implementation, over a pluggable
[call system](runtime/call-system.md) (JSON-RPC, a compact binary framing, or
your own).

## Where things are owned

| Concern | File | Owner | Frozen into CAS |
|---|---|---|---|
| Schema shape, package identity, which languages are supported | `config.idp` | package **author** | yes |
| Output location, layout, which versions to emit | `comline.toml` | **consumer** | no |

See [Packages & dependencies](packages/index.md) for the manifest, and the
[Design](../design/index.md) section for the reasoning behind the split.
