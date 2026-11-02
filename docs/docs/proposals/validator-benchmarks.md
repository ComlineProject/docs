# Validator benchmarks

Status: **draft** · Raised by [bounds on types](type-bounds/max-only.md#what-a-validator-minimum-costs),
where Proposal D's case rests on what a validator costs · Builds on the
[benchmark gates](shared-runtime-core/verification.md#benchmark-gates)

**The question:** what does running a validator cost, compared with decoding
alone and with a check done inside the decoder, and how is that measured so
it can't silently regress?

Where things stand:

- **Validators run only in Rust,** and only when asked
  ([Validators, phase 4](../design/validators.md#phase-4-runtime-enforcement-design)).
  - Generated types implement `Validate`: `validate()` collects every failure,
    `validate_first()` stops at one.
  - On receipt they run only when the consumer sets `validate_on_decode` to
    `"collect"` or `"first"`; the default is `"off"`.
  - A struct then decodes into an unchecked shadow type and is checked in a
    separate pass. Function parameters are checked by the dispatcher after
    decoding.
  - TypeScript doesn't generate validators yet
    ([core#96](https://github.com/ComlineProject/core/issues/96), step 4d).
- **No benchmark covers validators.** The runtime's benchmarks measure
  encoding, decoding, framings, the handshake and a connection step.
- **The runtime's Rust benchmarks measure hand-written copies** of generated
  types (`runtime/core/benches/definitions`). A test proves each copy encodes
  to the same bytes as its shape. Validators can't be measured that way: the
  code under test *is* what the generator emits.
- **The cost question is open in [bounds on types](type-bounds/max-only.md#what-a-validator-minimum-costs):**
  a minimum as a validator is a second pass over each string, but by how much
  is unmeasured.

## Proposal

### What is measured

Every case runs against a baseline, the same value decoded with validation
off, so the result is the cost validation adds.

| Case | What it isolates |
|---|---|
| **Decode, validation off** | the baseline |
| **Decode, `"first"`** | decoding plus fail-fast checks, through the shadow type |
| **Decode, `"collect"`** | decoding plus collect-all checks |
| **`validate()` alone,** on a value already decoded | the checks without decoding |
| **Params through the dispatcher** | the path function arguments take: decode, then `validate_first` |
| **A prototype in-decoder check** | the same minimum checked inside the decoder: the cost a [lowered validator or a bound](type-bounds/max-only.md#what-a-validator-minimum-costs) would have. Hand-written, benchmark only, never shipped |

**Shapes,** each in `packed@1` and `json@1`:

| Shape | What it stresses |
|---|---|
| `string-min-short` | `StringBounds(min_chars = …)` on a 16-character ASCII string |
| `string-min-long` | the same on 4096 characters: the second pass's cost grows with length |
| `string-min-unicode` | the same on non-ASCII text, where counting characters isn't counting bytes |
| `array-non-empty-1`, `array-non-empty-1000` | "at least one item" on 1 and on 1000 items |
| `nested-1000` | 1000 structs in an array, each with a check: the walk over every field |
| `no-checks` | a struct whose fields have no validators: proves it costs nothing (no shadow type is generated) |

**The failing path,** for `"first"` and `"collect"`: a value that fails on its
first field, and one that fails on its last. It's what a peer sending invalid
messages costs a receiver.

### The definitions: shared, in the corpus

`runtime/conformance/benches/` gains a `validators` definition next to
`formats.json`, so every language measures the same work:

- **`validators.ids`:** the schema, with the validators each shape uses. The
  existing definitions describe types in the corpus's own encoding, which has
  no validators. A schema is what a generator takes as input anyway.
- **`validators.json`:** each shape's type in that schema, a valid value, and
  the failing values, in the corpus's value encoding.
- **Ids** follow the existing scheme:
  `validator/<case>/<shape>/<format>`, e.g.
  `validator/decode-first/string-min-long/json@1`.

### Where it runs: in each generator's repository

Validators are generated code, so they're measured where they're generated:

| Language | Where | How |
|---|---|---|
| Rust | **comline-rust** | a benchmark crate generated from `validators.ids` at build time, run under `iai-callgrind`. Its tests already generate and compile crates (`codegen/tests/compiles.rs`), so the plumbing exists |
| TypeScript | **comline-typescript**, once step 4d ships validators | the same definitions, measured as the [verification design](shared-runtime-core/verification.md#benchmark-gates) says for a JIT language |
| Each later language | its generator's repository | its host's metric |

The prototype in-decoder check lives only in the benchmark crate, written by
hand next to the generated code it's compared with.

### Metric, gate and reports

The same as the runtime's, so nothing new is learned twice:

- **Rust: instruction counts,** base against head in the same job.
- **The gate:** a pull request fails when a benchmark grows more than the
  threshold over its base. The ledger of accepted regressions works as
  `runtime/core/benches/accepted-regressions.toml` does.
- **Reports:** the measured counts published to the repository's `reports`
  branch as `rust.validators.bench.json`, in the runtime's report format, for
  the docs to render.

### Phasing

1. **Definitions** in the corpus: `validators.ids` and `validators.json`.
2. **Measure only,** in comline-rust: the numbers published, no gate. This
   answers the question bounds on types is waiting on.
3. **Gate,** once the noise of these benchmarks is known. Thresholds come from
   noise measured at rollout, as the verification design says, not chosen in
   advance.
4. **TypeScript,** after step 4d.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Hand-written copies in the runtime, like its other benchmarks | measures a copy of the generated checks, which drifts from what the generator emits; the existing copies are only safe because a test compares their bytes, and checks have no bytes to compare |
| One benchmark in `generation`, the codegen kernel | the kernel decides *what* to check but emits no code; the cost is in each language's lowering |
| Wall time on shared runners | too noisy to compare anything (see the verification design) |
| Measuring only `validate()`, not decoding | misses the shadow type and the separate pass, which is most of the cost in question |

## Open

- **Placement:** definitions in the runtime's corpus and measurement in each
  generator's repository, as proposed, or everything in one place.
- **Measure first, gate later,** as proposed, or gate from the start.
- **The prototype in-decoder check:** worth building for the comparison, or
  wait until a lowered validator or a bound exists to measure for real.
- **Formats:** `packed@1` and `json@1`, or `msgpack@1` too.
- **Which validators beyond `StringBounds`:** the std `NonEmpty` and
  `IntRange` that [Proposal D](type-bounds/max-only.md) would need don't exist
  yet. Their shapes join when they do.
