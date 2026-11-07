# Language Guides

The [IDL guide](../guides/idl/index.md) covers writing a schema; [Code
generation](../guides/codegen/index.md) covers turning it into source. This
section is the third piece: actually *using* the generated code at run
time — spawning a client, serving a protocol, picking framing and wire
format, and (for Rust) fitting the runtime into a sync or async program.

Each language gets its own tree. Pick one from the tabs on the left.

## Status

| Language | Generator | Modes | Runtime |
|---|---|---|---|
| [Rust](rust/index.md) | shipped | `code`, `lib` | `comline-runtime`, `no_std`-first; sync, or async with `async = true` |
| [TypeScript](typescript/index.md) | shipped | `code`, `lib` | `@comline/runtime`, async/Promise-based |
| Python, Lua, Luau, C | none yet | — | — |

Python, Lua, Luau and C appear in example `config.idp` manifests and design
sketches, but no `comline-codegen-*` crate exists for them today — there is
nothing to generate and no runtime to link against.

## What each runtime speaks

Both runtimes speak every built-in framing, `packed@1` and `json@1`, and are
byte-compatible with each other. MessagePack is Rust only for now, and so is
TCP: TypeScript ships an in-memory transport and you bring your own for
anything else. The full matrix, proven against the conformance corpus, is in
the [language reference](../reference/languages/index.md#runtimes-side-by-side).

## Before the per-language pages

Framing and wire format are two independent axes — which is laid out
language-agnostically in [Call systems &
serialization](../guides/runtime/call-system.md). Read that first if the
distinction isn't already clear; the per-language pages below are the
concrete API, not the concept.
