<!--
---
icon: simple/typescript
---
-->

# TypeScript

Not published to npm yet. Depend on it from a git checkout or workspace
reference until it is; `comline-codegen-typescript`'s own pin on the
runtime (by git rev, like the rest of this toolchain) is the pattern to
copy.

## What you use

Which generated items you use depends on the protocol's framing and on who
provides it. The names below are for protocols `Chat` (the server provides it)
and `Events` (the client does), and `Mail` and `Rpc` for the others.

| Case | You implement | To serve | To dial | To call through |
|---|---|---|---|---|
| **The default connection**: every protocol on one [connection](connections.md), `datagram@3` | each protocol's interface: `Chat`, and `Events` for what the client provides. Handlers take the peer first | `serve(transport, { chat })`. `accept(transport, { chat })` takes the same and hands back the connection | `connect(transport, { events })`, or `connect(transport)` when the client provides nothing | `new ChatSender(conn).send({ n })`, on what `connect` returns, what `accept` returns, or the peer a handler is given |
| **The lockstep `datagram`**: one protocol per transport ([lockstep](client-and-server.md)) | the protocol's interface: `Mail` | `serveMail(impl, transport)` | `MailClient.connect(transport)` | `MailClient`'s methods |
| **JSON-RPC**, a protocol the client provides | as the default connection | as the default: the package's `serve` opens the connection with `JsonCodec` and `JsonRpcConnectionFraming` ([over JSON-RPC](connections.md#over-json-rpc)) | as the default | as the default |
| **JSON-RPC**, a server-only protocol | the protocol's interface: `Rpc` | `serveRpc(impl, transport)` | `RpcClient.connect(transport)`, encoding JSON | `RpcClient`'s methods |
| **By hand** | the same interfaces | `Connection.accept(transport, Format, CONNECTION_IR_HASH, new Datagram3Framing(), handshake())`, then `new ChatDispatcher(chat).provideOn(conn)` ([by hand](connections.md#by-hand)). Lockstep: `new Server(new MailDispatcher(mail), codec, framing).serve(transport, IR_HASH)` | `Connection.connect(…)`, the same way. Lockstep: `Client.connect(transport, codec, IR_HASH, framing)` | the same senders and clients |

A package whose protocols disagree on the framing or the handshake has no one
connection, so no `serve` or `connect`; each protocol keeps its own dispatcher
and sender ([when they're generated](connections.md#when-theyre-generated)).

### What's in the generated files

A package with a connection gets `connection.ts`. It opens with a comment
saying which of the above to use, for this package's protocols, and holds
`Services`, `ClientServices`, `accept`, `serve` and `connect`. In `lib` mode the
package's `index.ts` opens with a comment of the same kind, and lists each lockstep
protocol's `serve<Protocol>` and `<Protocol>Client.connect` too. A lockstep
protocol's own file has no such comment.

The package's `Format` (its codec) and `CONNECTION_IR_HASH` (the digest the
handshake checks) are shared by every file of the package. When more than one
file needs them they're in a `wire.ts` of their own, which `connection.ts`
re-exports; a lone file keeps its own.

What is marked `@internal` is wire plumbing: the `…ParamsLayout` constants, the
`…_CALLS` tables, the dispatchers of a connection, `provideServices` and
`provideClientServices`, and what the `comline@2` handshake is built from
(`HELLO`, `handshake()`). It stays exported, for by-hand use, and is not what you
call.

## The mirror fact to Rust's

Where the Rust runtime can choose to be sync or async by design, the TypeScript
runtime is **async/`Promise`-based throughout**,
`Client.connect`, `client.call`, `Server.serve`, every generated method. There's no sync
mode, so there's no equivalent of the Rust guide's concurrency page: using
it from async code is simply using it as it's already written, with `await`.

## On the shared core

Part of the runtime is the Rust [shared runtime core](../../proposals/shared-runtime-core/index.md),
loaded through wasm (the [C ABI](../../reference/languages/c-abi.md#wasm32-and-the-js-glue)),
and part is still TypeScript. The core is vendored into the package, pinned
to a `runtime` revision by `scripts/vendor-core.sh`
([ts#87](https://github.com/ComlineProject/comline-typescript/pull/87)).

| Runs on the core, once it has loaded | Stays in TypeScript |
|                          ---         |          ---        |
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
|    ---   |    ---:    | ---: |  ---:  |
| `datagram@2` round trip, 16 B | 44,902 | 42,072 | -6.3% |
| `datagram@2` round trip, 4096 B | 74,892 | 59,105 | -21.1% |
| `jsonrpc@1` round trip, 16 B | 189,461 | 54,782 | -71.1% |
| `jsonrpc@1` round trip, 4096 B | 626,016 | 104,459 | -83.3% |
| name hash | 14,468 | 1,121 | -92.3% |
| handshake | 33,578 | 5,763 | -82.8% |

## Where to go next

- [Connections](connections.md) — the default: every protocol on one
  connection, calls in both directions.
- [Lockstep `datagram`: client & server](client-and-server.md) — the lockstep
  framing's `<Protocol>Client`, dispatcher and `serve<Protocol>`, and the shape
  codegen emits for them.
- [Framing & wire format](framing-and-wire-format.md) — what's pluggable
  today and what isn't yet.
