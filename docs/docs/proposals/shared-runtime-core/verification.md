# Verification: differential fuzzing and benchmark gates

Status: **accepted** · part of [Shared runtime core](index.md) · stage 1 in progress

**The question:** with ten or more language runtimes and generators, how does
each one stay byte-identical to the others, exactly as strict as the others
about what it refuses, and fast? Byte vectors only cover the cases someone
wrote down.

The evidence that vectors alone aren't enough:

- **The corpus found five real TypeScript interop bugs the day it landed**
  (runtime#13, comline-typescript#50):
  - JSON absent-value handling;
  - optional-field omission;
  - `bigint` going through `Number`;
  - JSON-RPC id and payload precision above 2^53;
  - a missing-id response read as id 0.

  Each was found only because a case happened to exist for it.
- **comline-typescript#57 is still open.** TypeScript decoding accepts an
  unknown enum variant and an out-of-range integer. It was found only when
  runtime#21 added `decode-unknown-variant` and `decode-wider-integer-overflow`
  cases. Every other way a decoder can be too lenient has no case yet, so
  nothing would catch it.
- **Nothing measures speed.** A runtime can get twice as slow and every check
  stays green.

The user's constraint (see [the umbrella page](index.md#the-constraint)) says
none of correctness, conformance or performance may be lowered, in any
language. This stage is what lets CI enforce that. Stages
[2](core-interface.md), [3](generated-codecs.md) and 4 are judged by the numbers
it produces.

## What's built

Built 2026-10-25 and 2026-10-26, in [`runtime`](https://github.com/ComlineProject/runtime)
except where noted.

- **A pinned toolchain**
  ([runtime#30](https://github.com/ComlineProject/runtime/pull/30)): the
  toolchain is stable 1.98.0. The old `nightly` file had overridden the CI
  matrix, so stable was never actually tested.
- **`decode_seed` on every format**
  ([runtime#31](https://github.com/ComlineProject/runtime/pull/31)): `Json` and
  `MsgPack` gained `decode_seed`, as `Packed` has. `decode` goes through it,
  so a seeded decode and a derived one can't differ.
- **The reference decodes any generated shape**
  ([runtime#32](https://github.com/ComlineProject/runtime/pull/32)), through
  `TypeSeed`.
  - `Type` covers all scalars to 128 bits, unit, option, `T[]`, `T[N]` (N > 32
    included), struct and enum.
  - `tests/seed_vs_derive.rs` holds it to real serde derives on valid bytes,
    every single-byte mutation, truncation, a trailing byte, and hand-written
    JSON and MessagePack maps. Three planted seed bugs each fail it.
  - 14 new vectors per format.
- **`comline-reference`, the reference process**
  ([runtime#34](https://github.com/ComlineProject/runtime/pull/34)). It speaks
  NDJSON on stdio, protocol 1, and its ops are append-only. The
  [README](https://github.com/ComlineProject/runtime/blob/main/runtime/reference/README.md)
  has the protocol.
  - **This differs from the sketch below.** Requests carry the vectors' own
    `op`, `input` and `bytes`, so any vector case is a valid request. Replies
    are `bytes`, `accept` with `input`, `not_implemented` or `error`.
  - It also has `check` and `version`. An encode-only op given bytes answers
    `error`, never a refusal.
- **Properties and fuzz targets**
  ([runtime#37](https://github.com/ComlineProject/runtime/pull/37)): proptest
  properties and four cargo-fuzz targets, `decode_no_panic`,
  `packed_canonical`, `framing_decode` and `seed_vs_derive`.
  - CI runs them on every pull request, 60 seconds per target. A nightly run
    takes 10 minutes per target plus proptest at 100,000 cases, and opens an
    issue on a finding.
  - Findings so far:
    - JSON read some `f64` values one ulp off. Fixed with serde_json's
      `float_roundtrip`, and `found-f64-exact-digits` added to the vectors.
    - `packed@1` couldn't read back an array of elements that take no bytes.
      See core#141 below.
- **Instruction-count gates**
  ([runtime#35](https://github.com/ComlineProject/runtime/pull/35)):
  iai-callgrind 0.16.1, 58 benches, comparing base against head in the same
  job. Shared definitions live in `runtime/conformance/benches/`.
  - The limit is `ir=1%`. Measured noise was 0 instructions across three runs.
  - A planted 20-iteration slowdown in the handshake encoder failed the gate
    at +6.25%.
  - Lessons: the base must build into its own target directory, or Cargo
    reuses its build for the head; and `codegen-units = 1` for benches stops
    unrelated benches moving.
- **Core refuses an array of a type with no data**
  ([core#141](https://github.com/ComlineProject/core/pull/141)): `T[]` where
  the element type carries no data is `validation::array-of-dataless-type`.
  The user chose this over relaxing `packed@1`'s "count no larger than the
  bytes left" guard. It was cascaded to every tool
  ([cli#103](https://github.com/ComlineProject/cli/pull/103),
  [language-server#86](https://github.com/ComlineProject/language-server/pull/86),
  [playground#100](https://github.com/ComlineProject/playground/pull/100), the
  generators and generation), and the vector
  `format-packed/reject-count-past-input` pins the decoder side.
- **Connection sequences**
  ([runtime#39](https://github.com/ComlineProject/runtime/pull/39)):
  - a proptest model test of the sans-IO `State`, ordered and unordered, under
    `datagram@2` and `jsonrpc@1`, 20,000 cases each. Two planted `State` bugs
    were both caught; no bugs were found;
  - a `session` op in `comline-reference` with the events `call`, `receive`,
    `abandon` and `reply`, so another language can drive its own connection
    through the same events and compare frames and events.
- **TypeScript's differential harness**
  ([comline-typescript#76](https://github.com/ComlineProject/comline-typescript/pull/76)):
  fast-check properties against `comline-reference`, covering the formats, the
  framings, the envelope and the handshake. Pull requests run a short suite;
  a nightly run takes 20,000 cases.
  - The corpus was re-vendored to include the new vectors.
  - `known-divergences.json` lists each divergence class with its issue. A
    divergence is matched to a class by what is wrong with the input, in the
    direction the issue describes; anything else fails. #57 shows up as
    reported, not failed.
  - A planted off-by-one in the varint writer first went unnoticed: no
    generated string or array reached 128 elements. The generators now draw
    long ones around the varint boundaries, and the bug failed 6 runs of 6.
  - Fixed in TypeScript: `json@1` accepted a fixed-size array of the wrong
    length; `json@1` and `jsonrpc@1` replaced invalid UTF-8 and skipped a
    byte-order mark; the JSON reader accepted an escaped lone surrogate.

## Found along the way

Open issues the work turned up:

- [runtime#33](https://github.com/ComlineProject/runtime/issues/33): trailing
  bytes are accepted by `msgpack@1`, the envelope and the handshake, in both
  runtimes.
- [runtime#38](https://github.com/ComlineProject/runtime/issues/38): `json@1`
  writes NaN and infinity as `null`, which the receiver refuses.
- [runtime#40](https://github.com/ComlineProject/runtime/issues/40):
  `jsonrpc@1` reads a frame with only an id as a successful null reply.
- [comline-rust#76](https://github.com/ComlineProject/comline-rust/issues/76):
  generated Rust params borrow `&str`, so a JSON string with escapes is
  refused.
- [runtime#41](https://github.com/ComlineProject/runtime/issues/41):
  `jsonrpc@1` refuses a method name written with any escape, and writes a
  name that needs one unescaped, producing invalid JSON.
- [runtime#42](https://github.com/ComlineProject/runtime/issues/42):
  `jsonrpc@1` accepts invalid UTF-8 inside members it ignores.
- In TypeScript, each listed as a known divergence:
  [comline-typescript#73](https://github.com/ComlineProject/comline-typescript/issues/73)
  (`json@1` decoding doesn't check a value's shape against its type),
  [#74](https://github.com/ComlineProject/comline-typescript/issues/74)
  (`json@1` writes an `f32` with a double's digits) and
  [#75](https://github.com/ComlineProject/comline-typescript/issues/75)
  (`jsonrpc@1` takes duplicate members and integers spelled as floats).

## What's left

- **TypeScript connection sequences** against the reference's `session` op.
- **Coverage-guided fuzzing and wall-time benchmarks for TypeScript**, on a
  self-hosted `comline-bench` runner, which the user will register.
- **Fuzz and benchmark results in the language reference.** The
  [Rust](../../reference/languages/rust.md#verification) and
  [TypeScript](../../reference/languages/typescript.md#verification) pages show
  each runtime's verification, and TypeScript's divergence classes are
  rendered from `known-divergences.json`. Benchmark results fill in when a
  runtime checks in its `*.bench.json` (Rust's workflow only uploads it as an
  artifact so far). Fuzz results wait on a `*.fuzz.json` that no runtime
  writes yet.
- **A re-baseline path for the gate.** A correctness fix that costs time needs
  a deliberate way to move the baseline (see [Budgets](#budgets)). It isn't
  built yet.

The rest of this page is the plan as proposed. Where it describes something
that has since changed, it says so.

## Where things stand

As of the proposal, before the work in [What's built](#whats-built).

- **The wire corpus**, `runtime/runtime/conformance/` on `main`:
  - `features.json` lists 9 wire features. `vectors/<feature>.json` holds 163
    cases, 37 of them `"expect": "reject"`.
  - `format-packed` has 44 cases (12 rejections), `format-json` 31,
    `format-msgpack` 31, `framing-datagram2` 12, and the handshake 9.
  - The cases are computed from `comline-runtime` in `src/lib.rs` (1,667 lines).
    `vectors_are_current` fails when the checked-in files differ, and
    `CONFORMANCE_BLESS=1` rewrites them.
  - `profiles/<encoding>.json` states facts such as `unknown_variant: rejected`,
    each proven by named cases.
  - `support/rust.json` and `reports/rust.json` hold the claims and their proof.
    `docs/scripts/sync-language-support.py` renders the reports into the
    [language reference](../../reference/languages/index.md).
  - The counts are from the proposal. runtime#32 added 14 vectors per format,
    and the findings above added more.
- **The value model was small.**
  - `Value` covers the fixed-width numbers, strings, arrays, tuples, options,
    structs and unit variants.
  - `Type`, which a `decode` case reads into, covers `bool`, `u32`, `i32`,
    `string`, options, structs and enums.
  - The reference decodes into three hand-written reader types (`Point`,
    `Tagged`, `Color` in `mod readers`). Any other type is `NotImplemented`.
    So the reference couldn't decode an arbitrary schema's type. It can now
    (runtime#32).
- **The TypeScript runner** is `comline-typescript/runtime/test/conformance.test.ts`
  (589 lines).
  - It vendors the corpus at the commit in `runtime/test/conformance/VECTORS_REV`,
    and `scripts/vendor-conformance.sh --check` runs in CI.
  - It builds a `Layout` from each case's value or type and drives
    `PackedCodec`, `JsonCodec` and the framings.
  - `runtime/conformance-support.json` claims `format-json` as `partial`, with
    the two #57 cases listed as `failing`, and `format-msgpack` as
    `unsupported`.
- **The codegen corpus** (`generation/conformance/`) checks golden output and
  `SUPPORT` claims. It proves what a generator emits, not what the emitted code
  does on the wire.
- **There was no fuzzing anywhere in the org.** No repository had a fuzz
  target, `proptest`, `fast-check`, Jazzer or Atheris (checked on every
  repository's default branch, 2026-10-25). Rust has them now (runtime#37);
  no other language does yet.
- **There was one benchmark, and it isn't a gate.** `core/benches/parser_benchmark.rs`
  is a Criterion benchmark of the IDL parser, run by hand through
  `run_bench.sh`. No CI job runs it. The runtime now has gated benchmarks
  (runtime#35); generated code has none.

## Differential fuzzing

### The reference process

**The Rust runtime is the reference,** as it already is for the vectors.
"Correct" means "does what `comline-runtime` does". When a fuzzer finds Rust
itself wrong (it accepts what its profile says it refuses, say), Rust is fixed
and the change is reviewed as a wire change, the same way a re-blessed vector
is today.

The reference isn't trusted blindly, though. Rust gets its own fuzz targets
(see [What gets fuzzed](#what-gets-fuzzed)) for properties that need no second
implementation.

### How a fuzzer in another language talks to it

| Option | How | Works before stage 2 | Cost |
|---|---|---|---|
| **(a) `comline-reference`, a process** | A binary built from the runtime repository, speaking a line protocol on stdin and stdout | yes | One process round trip per batch. Needs a native binary on the CI runner. |
| **(b) The reference linked in** | Through the stage 2 C ABI or WASM build | no | In-process and fastest. But once a language's framing *is* the core, fuzzing that framing against the core compares the core with itself. |
| **(c) A generated corpus** | Rust writes millions of random cases to files; each language replays them | yes | No process at all. No coverage guidance: language X's fuzzer can't steer toward its own unexplored branches, and mutated inputs X invents never reach the reference. |

**Recommended: (a).**

- It is the only option that works today and keeps the fuzzer in the host
  language, where coverage guidance sees the host's code.
- It is versioned the same way as the vectors. The reference is built at the
  commit in `VECTORS_REV`, so a language's CI answers the same way on every
  run. Every language CI that vendors the corpus already has, or can install,
  a Rust toolchain (comline-typescript's CI has one for its codegen).
- **(b) comes later as an option, not a replacement.** Once stage 2 exists, a
  language may link the reference in-process for speed. Codecs stay native
  ([stage 3](generated-codecs.md)), so the differential check stays
  meaningful there. For framing it then checks the binding, not the logic.
- **(c) falls out of (a)** for free: the reference can dump a batch of cases to a
  file. That is useful for a host where spawning a process is awkward, but it
  is not the main path.

**The protocol,** as built in runtime#34. It is newline-delimited JSON, using
the conformance corpus's own encoding: a request carries a vector case's `op`,
`input` and `bytes`, so there is nothing new to learn:

```json
{"id": 1, "op": "encode", "input": {"format": "packed@1", "value": {...}}}
→ {"id": 1, "bytes": "0102..."}
{"id": 2, "op": "decode", "input": {"format": "packed@1", "type": {...}}, "bytes": "0102..."}
→ {"id": 2, "accept": true, "input": {...}}   or   {"id": 2, "accept": false}
```

- The ops are the corpus's ops (`name_hash`, `handshake`, `envelope`,
  `request`, `response`, `encode`, `decode`), plus `check` and `version`.
  `session`, for [connection sequences](#connection-sequences), was added in
  runtime#39.
- **Requests can be batched,** many to a line, so one round trip covers a
  fuzzer's whole batch. The batch size is the fuzzer's to choose.
- **A refusal carries no reason.** Rust's formats collapse every decode
  failure into `RuntimeError::Serialization`, so the reasons are already not
  part of the contract. What must agree is *whether* bytes are refused.

**What the reference needed: decoding a type it has never seen.** It decoded
only `Point`, `Tagged` and `Color`. A fuzzer sends random schemas, so the
reference has to decode by a type description at run time. It does now
(runtime#32).

- **The building block is there.** `Packed::decode_seed` exists for this
  purpose. The simulator's `src/packed.rs` (~790 lines) already drives the
  runtime's `packed@1` serializer and deserializer from a run-time `TypeDef`,
  and `serde_json` and `rmp-serde` take a `DeserializeSeed` the same way.
- **The risk is that a schema-driven path behaves differently from what
  generated Rust does,** which is `serde` derives. The reference's seed must make
  exactly the deserializer calls a derive makes (`deserialize_struct` with the
  field names, `deserialize_enum` with the variant names, and so on). This is
  checked two ways:
  - the reference passes the whole conformance corpus;
  - a Rust fuzz target decodes the same bytes through the seed and through
    derived types, for a fixed set of shapes, and requires the same answer.
- **The value model grew** to every shape a generated type can have, except
  tagged unions. The vectors gained these shapes at the same time, so the
  corpus and the reference never describe different worlds.

### What gets fuzzed

| Target | Property | Inputs |
|---|---|---|
| **Value → bytes** | For every format a language claims, encoding a value gives exactly the reference's bytes. JSON compares by the corpus's `"compare": "json"` rule. | random schema, random value of it |
| **Bytes → accept or refuse** | Both accept or both refuse. If both accept, the values are equal. | valid encodings, then mutated ones |
| **Framing and handshake** | Request and response frames encode identically and decode identically, including refusals. | random call ids, request ids, protocol numbers, envelopes and payloads; mutated frames |
| **Connection sequences** | The same sequence of events gives the same frames and the same events out. | a generated sequence, see below |

**Strictness parity is the point of the second row.** Mutations aim at
exactly the places a lenient decoder gets wrong:

- overlong varints, and lengths or counts past the end of the input;
- `bool` and option tags other than `00` and `01`;
- bad envelope tags and unknown frame kinds;
- trailing bytes after a complete value;
- integers out of range for the field, such as a JSON `2^40` in a `u32`;
- unknown enum variants, by index or by name;
- invalid UTF-8, and truncation at every offset.

Random byte flips find the rest. Coverage guidance (below) steers mutations
toward decoder branches no case has reached yet. comline-typescript#57 is
exactly the kind of bug this row finds by itself.

**Rust's own targets** need no second implementation:

- decoding never panics and never allocates more than the input justifies (the
  `packed@1` module promises to refuse an oversized length before allocating);
- for `packed@1`, if bytes decode, re-encoding gives the same bytes. The format
  promises one encoding per value;
- the profile facts hold for random inputs, not only for the named cases.

These are the proptest properties and fuzz targets of runtime#37.

### Connection sequences

The connection state machine is behaviour, not bytes. It is fuzzed
model-based:

- A sequence is a list of events:
  - a local call (protocol, call, one-way or not);
  - an incoming request frame;
  - an incoming reply, whose request id is matching, stale or never issued;
  - an abandoned call (a timeout);
  - a malformed frame.
- Both sides run the sequence. The frames they emit must be byte-identical,
  and the events they report must be the same: `Request`, `Reply` for a given
  id, `Stale`, or an error.
- In Rust the subject is the sans-IO `State` in `runtime/core/src/connection.rs`
  (`encode_request`, `encode_reply`, `receive`, `abandon`).
- **TypeScript has no separate state machine.** Its `Connection`
  (`runtime/src/connection.ts`) owns the read loop, so its harness drives it
  over an in-memory transport. After stage 4, if TypeScript's connection
  logic is the core, this target checks the binding instead of the logic.

### Random schemas, not only random values

Values of a few fixed types won't find a bug that needs a struct nested in an
option in an array. The generator draws schemas too:

- **It produces frozen IR directly,** as `generation/conformance` builds its
  fixtures as `Vec<FrozenUnit>`, rather than `.ids` text. The parser has its
  own tests; going through it here would only slow the loop down.
- **Depth and size are bounded,** so a run spends its time on many schemas,
  not one huge one.
- **There are two tiers:**
  - **Runtime tier.** The language builds its codec description from the
    random schema at run time. TypeScript's runner already does this
    (`layoutOfType`). This is cheap and runs per pull request.
  - **Generated tier.** `comline generate` runs over the random schema, the
    output is compiled and the fuzzer drives the generated code. That is what
    users run, and it is the only tier that covers the generator. It is slow
    per schema, so it runs nightly. Once [stage 3](generated-codecs.md) makes
    codecs generated per type, this tier becomes the main one, and the pull
    request job runs it over a fixed set of pre-generated schemas.
    The user decided this tier starts with stage 3.

### Fuzzing engines

Use coverage-guided fuzzing where the language has it, and property-based
testing with shrinking elsewhere:

| Language | Coverage-guided | Property and model-based |
|---|---|---|
| Rust | `cargo-fuzz` (libFuzzer) with `arbitrary` | `proptest` |
| TypeScript | Jazzer.js | `fast-check`, including `fc.commands` for connection sequences |
| Python | Atheris | Hypothesis |
| Go | `go test -fuzz` (native) | the same, with structured inputs |
| Java | Jazzer | a property-testing library |

The property engine drives the structured targets (schema, value, sequence);
the coverage-guided engine drives the byte targets. A language with neither
gets a seeded random generator, which is weaker, and its report says so.

### Findings become vectors

A failure is minimized by the engine's shrinker (libFuzzer's `-minimize_crash`,
fast-check's shrinking), then **becomes a case in the conformance corpus**:

- The minimized input is added to `reference_cases()` in
  `runtime/conformance/src/lib.rs`, and the expected bytes or the refusal come
  from the Rust reference as for every other case. The id says where it came
  from, for example `format-packed/found-overlong-count`.
- From then on every language checks it on every run, and a new language
  inherits every bug found before it existed.
- **A known divergence is listed, not ignored.** While #57 is open,
  TypeScript's fuzzer will find it at once. Each language keeps a list of
  known divergence classes, each tied to an issue, as `conformance-support.json`
  lists `failing` cases. A finding in a listed class is reported, not failed.
  Fixing the issue removes the entry, and the class then fails if it comes
  back.
- Each engine's working corpus is seeded from the vectors and cached between
  runs.

### CI budget

| When | What | Budget |
|---|---|---|
| **Every pull request** | Runtime tier, every target, short | a few minutes in total, split across targets |
| **Nightly** | Every target, long runs, persistent corpora; the generated tier over fresh schemas | about an hour per language |
| **On a new `VECTORS_REV`** | The full corpus, plus a nightly-length run | as nightly |

These are starting values. A nightly failure opens an issue with the
minimized input rather than blocking a merge no pull request caused. A short
pull request run catches the obvious mistakes; the depth comes from nightly.

As built for Rust (runtime#37): 60 seconds per target on every pull request,
and a nightly run of 10 minutes per target plus proptest at 100,000 cases.

## Benchmark gates

### What is measured

The benchmark definitions are shared so every language measures the same
work. A `benches/` directory in the conformance corpus describes the shapes
and values, and is vendored with the vectors.

| Benchmark | Per | Shapes |
|---|---|---|
| **Encode, decode** | format (`packed@1`, `json@1`, `msgpack@1`) | small scalar struct; string-heavy struct; nested structs and options; a large array of small structs; enum-heavy |
| **Framing encode, decode** | framing (`datagram@1`, `datagram@2`, `jsonrpc@1`) | payloads of 16 B, 256 B, 4 KB and 64 KB |
| **Handshake** | | encode, decode, compare |
| **Connection step** | | issue a call, receive its reply |
| **Core crossing** (once [stage 2](core-interface.md) exists) | binding | an empty call, then one frame at each payload size above |

The last row is what [stage 4](index.md#stages) needs. For small frames, a
TypeScript call into WASM or napi may cost more than the work it replaces.
Only this row can say where that line is.

### Judging a regression without flaky CI

Shared CI runners are noisy. Wall-time differences of several percent between
identical runs are common there, so a wall-time gate on them would fail at
random or be set too loose to catch anything.

| Approach | Strength | Weakness |
|---|---|---|
| **Instruction counts** (Callgrind, as `iai-callgrind` does in Rust) | Deterministic. Runs on any runner. Fine thresholds work. | Blind to cache misses, branch mispredictions and memory bandwidth. Meaningless under a JIT (Node, the JVM, .NET), where counts depend on when the JIT kicks in. |
| **Wall time, base against head, on a dedicated runner** | Measures what users feel, under any runtime | Needs a dedicated machine (fixed CPU frequency, isolated cores). Still noisy: needs repeated, interleaved runs and a statistical test. |
| **Wall time on shared runners** | Free | Too noisy to gate on |

**Recommended: always compare base against head in the same job on the same
machine, never against a stored number.** The metric depends on the host:

- **Ahead-of-time compiled languages (Rust, C ABI bindings, Go, Swift and the
  like):** instruction counts are the pull request gate. They are cheap and
  exact enough to fail on a small regression.
- **JIT languages (TypeScript, Java, C#):** wall time on the dedicated runner,
  with interleaved base and head runs and a confidence interval. The gate
  fails only when the interval excludes "no change" and the slowdown is over
  the threshold.
- **Every language, nightly:** wall time on the dedicated runner. This catches
  what instruction counts can't see, so a memory-layout regression that passed
  the count gate is found within a day. A nightly regression opens an issue.

The noise doesn't go away. Instruction counts let some real regressions
through, and wall time on a dedicated runner still has a floor below which a
regression goes undetected until several accumulate; the nightly series is
what makes that drift visible. Thresholds are set from the noise measured
during rollout, not chosen in advance.

### Budgets

Each language has a budget per benchmark, in two parts:

| Language | Gate on pull requests | Ratio to Rust (nightly, dedicated runner) |
|---|---|---|
| Rust (reference) | instruction counts, against base | 1.0 by definition |
| TypeScript | wall time on the dedicated runner, against base | recorded at rollout, then ratcheted |
| Every new language | its host's metric, against base | recorded when it first ships, then ratcheted |

- **No regression against base** is the gate. A pull request that makes any
  benchmark slower beyond the threshold fails.
- **The ratio to Rust** is the cross-language comparison: each language's time
  for a benchmark divided by Rust's, on the same machine. It starts as
  whatever the language achieves when it first ships, and from then on it
  **only tightens**. Loosening it is an explicit, reviewed change to the
  budget file, with the reason recorded.
- **A correctness fix that costs time is never refused.** The constraint
  forbids losing correctness as much as losing speed. The pull request re-bases
  the budget with its cost recorded, and an issue tracks recovering it. Fixing
  #57 adds checks to TypeScript decoding, so it is the first case of this.
  The re-baseline path isn't built yet. The Rust gate (runtime#35) fails on
  any slowdown over its limit, whatever the cause.
- **The ratios are stage 4's evidence.** For each host and each piece
  (framing, handshake, connection), the native implementation and the core
  through its binding are both measured. The core replaces native code only
  where it is at least as fast at every measured size.

### Published results

Results are published the same way as the conformance reports:

- Each language writes `reports/<lang>.bench.json` (the ratios and the nightly
  series) and `reports/<lang>.fuzz.json` (targets, executions, corpus size,
  open divergence classes).
- `sync-language-support.py` renders them into the language reference next to
  the support tables.
- A pull request gets its comparison against base as a comment.

## How this enforces the constraint

| Standard | Enforced by |
|---|---|
| **Correctness** | Fuzzing: Rust's own property targets, and every language against the reference |
| **Conformance** | The vectors, plus fuzzing that turns each finding into a new vector |
| **Performance** | Benchmark gates against base, and ratios to Rust that only tighten |

**No language ships a feature without all three.** A runtime's support claim
for a feature is `supported` only when its vectors pass, its fuzz targets for
that feature exist and run in CI, and its benchmarks for it are gated. A
missing piece makes the claim `partial`, with the gap named in its note. The
support check enforces this the way it already enforces `failing` lists.

## Alternatives considered

- **Vectors only.** Rejected. They prove what someone thought to write down.
  All five bugs from runtime#13 and the two from #57 were found only after a
  case was written for each, and a random schema's shapes are never written
  down at all. Vectors stay as the floor and the record of findings, but they
  can't be the whole check at ten languages.
- **Property tests per language, without a reference.** Rejected. A round-trip
  property (`decode(encode(x)) == x`) holds for an encoding that is wrong
  symmetrically, and a decoder that accepts everything never fails it. So it
  catches neither byte incompatibility nor leniency, which are exactly the two
  bug classes found so far. Property engines are used here, but checked
  against the reference.
- **Manual benchmarks.** Rejected. `core/benches/parser_benchmark.rs` shows
  how it goes: a report someone opens in a browser, run when someone
  remembers, not comparable across languages, and blocking nothing. Under the
  constraint, a regression has to fail CI.
- **A stored baseline instead of base against head.** Rejected. Runner
  hardware and noise change under it, and a stored number goes stale.

## Open questions

- **Who maintains the dedicated benchmark runner.** It is a self-hosted
  runner, `comline-bench`, which the user will register. Wall time gates for
  JIT languages depend on it.
- **How the reference reaches language CI:** built from source at `VECTORS_REV`
  with `cargo install`, or a prebuilt binary attached to the runtime
  repository per commit.
- **Whether the simulator's schema-driven `packed@1` code moves into the
  `comline-reference` crate,** with the simulator depending on it, so that schema-driven
  decoding exists once.
- **Tagged unions in the value model.** The value model now covers every
  shape except them (runtime#32). They join when the
  [proposal](../tagged-unions/index.md) is decided.
- **Live cross-runtime calls.** The conformance README leaves behaviour such
  as one-way replies and timeouts to "live cross-runtime calls, later". The
  connection-sequence target covers part of that. Whether real processes over
  real transports are still needed is open.

## Rollout

Step 1 is mostly built; [What's built](#whats-built) and
[What's left](#whats-left) say what.

1. **Rust: `comline-reference` and the benchmarks.** The extended value model with
   schema-driven decoding and its seed-against-derive check, `comline-reference`,
   the random IR generator, Rust's own `cargo-fuzz` targets, the shared
   benchmark definitions with `iai-callgrind` gates, and the pull request and
   nightly CI jobs.
2. **TypeScript.** fast-check (values, schemas, sequences) and Jazzer.js
   (bytes) against the reference pinned by `VECTORS_REV`, with #57 entered as a
   known divergence class on day one. Benchmarks on the dedicated runner, with
   the native-against-core comparison added when stage 2 lands.
3. **The template for every new language:** vendor the corpus and `comline-reference`,
   implement the value and schema generators against the shared type grammar,
   provide the four fuzz targets and the shared benchmarks, and write the two
   reports. The language isn't listed in the language reference until every
   item is done.

## What it touches

- **`runtime`:**
  - `runtime/conformance/`: `Value` and `Type` extended; schema-driven
    decoding; findings added to `reference_cases()`; `benches/` definitions;
    `reports/rust.bench.json` and `reports/rust.fuzz.json`.
  - A new `comline-reference` crate and binary.
  - `runtime/fuzz/` with the `cargo-fuzz` targets.
  - `runtime/core/benches/`.
  - `.github/workflows/build_test.yml`, plus a nightly workflow.
- **`comline-typescript`:**
  - `runtime/test/fuzz/` and a benchmark harness.
  - `scripts/vendor-conformance.sh`, extended to vendor `benches/` and fetch
    the reference.
  - The known-divergence list, next to `conformance-support.json`.
  - `.github/workflows/ci.yml`.
- **`generation`:** the random frozen-IR generator, shared with
  `conformance`'s fixture builders, and the generated-tier harness.
- **`simulator`:** possibly, if its `src/packed.rs` moves into `comline-reference`.
- **`docs`:** `scripts/sync-language-support.py` renders the fuzz and bench
  reports. The language reference pages and the runtime guide's conformance
  section describe them.
- **Infrastructure:** one dedicated benchmark runner.
