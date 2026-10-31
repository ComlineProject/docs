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

## On the shared core

Part of the runtime is the Rust [shared runtime core](../../proposals/shared-runtime-core/index.md),
loaded through wasm (the [C ABI](../../reference/c-abi.md#wasm32-and-the-js-glue)),
and part is still TypeScript. The core is vendored at `runtime` `257bc02`
([ts#87](https://github.com/ComlineProject/comline-typescript/pull/87)).

| Runs on the core, once it has loaded | Stays in TypeScript |
|---|---|
| `nameHash` and the `comline@1` handshake frames | The read loop, scheduling and dispatch |
| With a built-in framing (`Datagram2Framing`, `JsonRpcConnectionFraming`): framing, request ids and waiting state, in `Connection` ([ts#89](https://github.com/ComlineProject/comline-typescript/pull/89)) | Custom framings, and everything when the core can't load (a strict CSP, say) |
| | Codecs, generated types, transports and the `Handshake` plug-in |

Behaviour is the same on either path, and the tests run each session on both.
A malformed frame closes the connection, a stale reply is dropped, and waiting is
unbounded (calls queue in order while the connection is busy). If the core traps,
its instance is poisoned: every connection on it fails with a `RuntimeError` of
kind `poisoned`, and the next connection loads a fresh core. A transport's
`send` also has a [rule about reusing frames](client-and-server.md#transport-today)
since larger frames are encoded into pooled arrays
([ts#88](https://github.com/ComlineProject/comline-typescript/pull/88)).

### What it costs

Instruction counts for one call and its reply through two `Connection`s over
`duplex()`, params and result both the given size, with no codec work. Measured
with the local `runtime/bench/count.py` (Callgrind) at the optimized V8 tier,
median of 5. They are not a CI gate; see
[how JavaScript is checked](../../proposals/shared-runtime-core/verification.md#how-javascript-is-checked).

| Workload | TypeScript | Core | Change |
|---|---:|---:|---:|
| `datagram@2` round trip, 16 B | 44,902 | 42,072 | -6.3% |
| `datagram@2` round trip, 4096 B | 74,892 | 59,105 | -21.1% |
| `jsonrpc@1` round trip, 16 B | 189,461 | 54,782 | -71.1% |
| `jsonrpc@1` round trip, 4096 B | 626,016 | 104,459 | -83.3% |
| name hash | 14,468 | 1,121 | -92.3% |
| handshake | 33,578 | 5,763 | -82.8% |

## Where to go next

- [Client & server](client-and-server.md) — connecting, serving, and the
  shape codegen actually emits.
- [Framing & wire format](framing-and-wire-format.md) — what's pluggable
  today and what isn't yet.
