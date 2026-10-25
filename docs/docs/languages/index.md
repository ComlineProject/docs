# Language Guides

The [IDL guide](../guide/idl/index.md) covers writing a schema; [Code
generation](../guide/codegen/index.md) covers turning it into source. This
section is the third piece: actually *using* the generated code at run
time — spawning a client, serving a protocol, picking framing and wire
format, and (for Rust) fitting the runtime into a sync or async program.

Each language gets its own tree. Pick one from the tabs on the left.

## Status

| Language | Generator | Modes | Runtime |
|---|---|---|---|
| [Rust](rust/index.md) | shipped | `code`, `lib` | `comline-runtime`, sync, `no_std`-first |
| [TypeScript](typescript/index.md) | shipped | `code` | `@comline/runtime`, async/Promise-based |
| Python, Lua, Luau, C | none yet | — | — |

Python, Lua, Luau and C appear in example `config.idp` manifests and design
sketches, but no `comline-codegen-*` crate exists for them today — there is
nothing to generate and no runtime to link against.

## Capability matrix

What each shipped runtime actually supports, independent of what the call
system [could in principle](../guide/runtime/call-system.md) support:

| | Transports | Wire formats | Framings |
|---|---|---|---|
| Rust | in-memory, TCP | packed, JSON, MessagePack | datagram@2, datagram, JSON-RPC |
| TypeScript | in-memory only | packed, JSON | datagram@2, datagram, JSON-RPC |

Not every combination of wire format and framing ships — JSON-RPC's own spec
is JSON text, so a `jsonrpc` + `msgpack`/`packed` pairing doesn't exist on
either side. MessagePack is Rust only, until TypeScript gets a codec for it.
`packed@1` and `datagram@2` are the built-in defaults; see
[Wire defaults](../guide/packages/index.md#wire-defaults).

## Who maintains this

There is no named maintainer per language today — the project is set up so
that doesn't become a single point of failure as more languages (and more
people) show up. Each language's generator and runtime live together in
that language's own repo under the `ComlineProject` GitHub org, which holds
the published-package namespace (the npm scope, the future crates.io name,
and so on for later languages). A contributor gets *publish rights*, not
ownership of the name — releases run through CI trusted publishing (OIDC),
not a personal token, so one maintainer stepping away never orphans a
published package.

The full reasoning is in [Runtime & generation repo
structure](../design/runtime-repo-structure.md#ownership-packaging) if
you want the detail; this page just needed to say it exists.

## Before the per-language pages

Framing and wire format are two independent axes — which is laid out
language-agnostically in [Call systems &
serialization](../guide/runtime/call-system.md). Read that first if the
distinction isn't already clear; the per-language pages below are the
concrete API, not the concept.
