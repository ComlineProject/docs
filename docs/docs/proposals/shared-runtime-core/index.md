# Shared runtime core

Status: **under discussion** · tracked in
[runtime#29](https://github.com/ComlineProject/runtime/issues/29) · direction
agreed 2026-10-25; stage 1 accepted and in progress (see
[what's built](verification.md#whats-built)); stages 2–3 are proposals below,
stages 4–5 are agreed

**The question:** today every Comline runtime is written from scratch in its
own language, and every runtime feature is built once per language. That
works for two languages. Comline aims at ten or more. How do runtimes stay
correct, conformant and fast at that scale without writing the same logic ten
times?

## The constraint

This was set by the user on 2026-10-25, and it governs every part of this
proposal:

> lets presume that comline in the future will have a lot of languages to be
> supported, possibly 10+, so nothing like correctness, conformance,
> performance and so on can be lost, there is in no moment that accepting
> lowering any standard will be possible to accept

Every option below is judged against correctness, conformance and performance
together. An option that gives up any one of them is rejected, however much
work it would save. Where a host makes a cost unavoidable, as browsers and Go
without cgo do, the cost is stated, and **measurement decides**, not taste.

## Where things stand

- **Two runtimes implement the same contract.**
  - [`comline-runtime`](https://github.com/ComlineProject/runtime) is in Rust.
  - [`@comline/runtime`](https://github.com/ComlineProject/comline-typescript)
    is in TypeScript: about 2,350 lines of source, nearly all of it mirroring
    Rust.

    | TypeScript file | Lines |
    |---|---|
    | `packed.ts` | 534 |
    | `json.ts` | 272 |
    | The three framings | 354 |
    | `connection.ts` | 261 |
    | `handshake.ts` | 181 |

- **Every wire feature this month was built twice.** Connections
  (runtime#23–#25, then comline-typescript#64), `datagram@2`, `packed@1`
  (comline-typescript#70) and the fault channel.
- **`packed@1` has three implementations:**
  - the Rust runtime's;
  - TypeScript's;
  - the simulator's, which is driven by the schema at run time.
- **Async exists only in Rust** (runtime#24). TypeScript ignores it
  (comline-typescript#68).
- **The copies drift.**
  - The [conformance corpus](../../reference/languages/index.md) found five real
    interop bugs in TypeScript the day it landed (runtime#13,
    comline-typescript#50).
  - comline-typescript#57 is still open: TypeScript decoding doesn't refuse
    unknown enum variants or out-of-range integers.
- **Generators duplicate too.**
  - The per-protocol glue is re-derived in each generator's `protocol()`:
    call tables, fault policy, error ordinals, and which framing and format
    a protocol gets ("JSON-RPC forces JSON").
  - The same bug has already been fixed twice, in comline-rust#28 and
    comline-typescript#32.
  - [How generators are built](../codegen-architecture/index.md) has the
    record.
- **There was no fuzzing anywhere in the org, and no runtime benchmark.** The
  only benchmark was core's IDL parser benchmark, which is run by hand and in no
  CI job. The corpus proved only the cases someone wrote down. Stage 1 has
  since added fuzz targets and gated benchmarks for Rust; see
  [what's built](verification.md#whats-built).

A third language would add roughly 2,000 runtime lines and a generator the size
of today's (2,184 lines in Rust, 1,635 in TypeScript), and repeat all of the
above. At ten languages it doesn't hold.

## How we got here

| When | What happened |
|---|---|
| 2023-11 – 2024-01 | The original design was this one: a Rust **core runtime**, with each language a thin runtime speaking to it. It was built as `package_abi` (`abi_stable` + `libloading`), `runtime-langs/{c,lua,luau,python}` (mlua cdylibs; pyo3 and cbindgen planned) and C-FFI generators. It stalled at stubs and `todo!()`. |
| 2026-08-31 | [One repository per language](../repo-organization/split-by-language.md) was accepted for **repository layout** reasons: each language's codegen and runtime share one CI, and native toolchains stay out of one workspace. Whether runtimes share code was not decided. |
| 2026-09-02 | The TypeScript runtime was written as a from-scratch port. |
| 2026-09-03 | The playground simulator dropped its TypeScript reimplementation for the real `comline-runtime` compiled to WASM, deleting about 3,400 lines (playground#38). **This is the working precedent.** |
| 2026-10-04 | docs#10 rewrote the [runtime guide](../../guide/runtime/index.md) to say there is "no FFI boundary". That was a docs correction of stale text, not a debated decision. This proposal reopens it. |
| 2026-10-18 | Byte-exact conformance vectors became the only thing keeping the runtimes in agreement. |

## The proposal

Split the work by what can cross a language boundary cheaply.

- **Bytes in, events out: one implementation.** The handshake, the framings,
  envelopes and the connection state machine work on bytes and integers. They
  are already sans-IO, `no_std` and allocation-free in Rust. They move behind
  a narrow, stable boundary that every language binds.
- **Typed values: generated, not shared.** Codecs work on each host's own
  objects. Converting those objects at a boundary on every call is slower
  than native code in every language, so codecs are generated as specialized
  native code instead. They come from **one** layout plan computed in the
  shared codegen kernel, so ten backends render one source of truth.
- **The host, natively.** Async, transports, generated types and the
  language's own idiom stay in each language. Because the core is sans-IO,
  that costs nothing.
- **Proof, not trust.** Every language is checked against the Rust reference
  by vectors, differential fuzzing and benchmark gates before anything moves.

### Stages

| Stage | Page | State |
|---|---|---|
| 1 | [Verification: differential fuzzing and benchmark gates](verification.md) | accepted, in progress |
| 2 | [One protocol core: a C ABI and WASM from one crate](core-interface.md) | proposal |
| 3 | [Codecs and protocol glue generated from one plan](generated-codecs.md) | proposal |
| 4 | Move TypeScript onto the core where the benchmarks allow | agreed |
| 5 | Clean up the leftovers and the documents that contradict this | agreed |

**Stage 1 comes first** because it is what turns "measurement decides" into a
rule CI enforces. Without it, stages 2–4 would be judged by opinion.

**Stage 4: moving TypeScript.**
- TypeScript is the first real test. For small frames, hand-written
  TypeScript framing may beat a WASM or napi call, because of the copy into
  WASM memory.
- Each piece moves only when the stage 1 gates show the core is at least as
  fast for that host. Otherwise it stays native and is held to the same
  vectors, fuzzing and gates.
- The browser has no native option at all. The playground simulator already
  runs the core there.

**Stage 5: the cleanup.**
- **Remove or split `runtime/core/src/package_abi`.** It pulls `abi_stable`
  and `libloading` under the `std` feature, which is what keeps `std` off
  wasm32 today.
- **Delete the dead code:** `runtime-langs/*`, `generation/lib-gen/*` and the
  unbuilt FFI modules in `comline-rust/codegen`.
- **Rewrite the [runtime guide](../../guide/runtime/index.md)** for the new
  model.
- **Resolve `design/core-target-contract.md`:**
  - §4.7, the open "per-language runtime ↔ core runtime seam", which this
    proposal answers;
  - §5, the FFI/dylib ABI.
- **Keep `dylib` mode separate.** It loads a generated package compiled to a
  stable-ABI object, which is a different idea from a shared runtime core.
  Mixing the two up is part of how the original design got lost.
  [Library generation](../../guide/codegen/library-generation.md) keeps it
  as its own planned feature.

### How it fits earlier decisions

- **One repository per language still holds.**
  - The core stays in `runtime`.
  - Each `comline-<lang>` repository holds that language's thin binding, its
    generator backend and its CI.
  - The generator and runtime of one language still agree within one CI.
- **The conformance corpus stays the cross-language contract.** Its job
  widens: stage 1 adds fuzzing and benchmarks around it, and its findings
  feed back in as vectors.
- **[Extending the call system](../extensibility.md)** defines an encoding as
  a name, a profile and vectors. That still holds. Whether a third-party
  encoding can also plug its rules into the layout plan, instead of shipping a
  codec per language, is an open question for
  [stage 3](generated-codecs.md).
