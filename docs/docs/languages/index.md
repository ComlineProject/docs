# Language Guides

The [IDL guide](../guides/idl/index.md) covered writing a schema; [Code
generation](../guides/codegen/index.md) covered turning it into source. This
section is the third piece: actually *using* the generated code at run
time — spawning a client, serving a protocol, picking framing and wire
format, and (for Rust) fitting the runtime into a sync or async program.

Each language gets its own tree. Pick one from the tabs on the left.

## Status

| Language | Generator | Modes | Runtime |
| --- | --- | --- | --- |
| [Rust](rust/index.md) | shipped | `code`, `lib` | `comline-runtime`, `no_std`-first; sync, or async with `async = true` |
| [TypeScript](typescript/index.md) | shipped | `code`, `lib` | `@comline/runtime`, async/Promise-based |
| [C](c/index.md) | none yet | — | `comline-runtime-ffi`, through the [C ABI](../reference/languages/c-abi.md) |
| Python, Lua, Luau | none yet | — | — |

Python, Lua and Luau appear in example `config.idp` manifests and design
sketches, but no `comline-codegen-*` crate exists for them today — there is
nothing to generate and no runtime to link against. C has no generator yet
either, but it has a runtime to link against: the C ABI.

## What each runtime speaks

Both runtimes speak the supported [built-in framings](../reference/wire/framings/index.md),
the supported [data formats](../reference/wire/formats/index.md) and are
byte-compatible with each other. MessagePack is Rust only for now, and so is
TCP: TypeScript ships an in-memory transport and you bring your own for
anything else. The full matrix, proven against the conformance corpus, is in
the [language reference](../reference/languages/index.md#runtimes-side-by-side).

## Before the per-language pages

Framing and wire format are two independent concerns, which are laid out
language-agnostically in [Call systems &
serialization](../guides/runtime/call-system.md). Read about them first if the
distinction isn't clear enough, since the per-language pages in this section are
the concrete API.
