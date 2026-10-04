# TypeScript

Status: shipped, `code` mode only — there's no `lib` mode for TypeScript
yet (Rust is the only language that has it; see [Library
generation](../../guide/codegen/library-generation.md)). Generated code
depends on **`@comline/runtime`** (MPL-2.0, ESM, Node).

Not published to npm yet. Depend on it from a git checkout or workspace
reference until it is; `comline-codegen-typescript`'s own pin on the
runtime (by git rev, like the rest of this toolchain) is the pattern to
copy.

## The mirror fact to Rust's

Where the Rust runtime is sync and blocking by design, the TypeScript
runtime is **async/`Promise`-based throughout** — `Client.connect`,
`client.call`, `Server.serve`, every generated method. There's no sync
mode, so there's no equivalent of the Rust guide's concurrency page: using
it from async code is simply using it as it's already written, with
`await`.

## Where to go next

- [Client & server](client-and-server.md) — connecting, serving, and the
  shape codegen actually emits.
- [Framing & wire format](framing-and-wire-format.md) — what's pluggable
  today and what isn't yet.
