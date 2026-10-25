# TypeScript

What Comline supports in TypeScript, as its conformance suites prove it. For how
to use it, see the [TypeScript guide](../../languages/typescript/index.md). The states are explained in the
[overview](index.md#what-the-states-mean).

## Code generation

What the [`comline-typescript`](https://github.com/ComlineProject/comline-typescript) generator emits
for each language feature, and the conformance fixtures that prove it.

<!-- codegen:start -->
<!-- Rendered from ComlineProject/generation's features.json by scripts/sync-language-support.py - don't edit by hand. -->

Generator `typescript#5.0`.

| Feature | What it covers | State | Proven by |
|---|---|---|---|
| structs <br><sub>`structs`</sub> | `struct` declarations | ✅ supported | `primitives`, `optional_and_arrays`, `type_refs`, `protocol`, `shapes`, `cross_schema`, `import_alias`, `import_glob`, `nested_namespace`, `external_std`, `validators`, `validators_on_decode`, `unions`, `large_fixed_arrays_nested`, `format_json` |
| enums <br><sub>`enums`</sub> | `enum` declarations | ✅ supported | `enum_basic` |
| optional fields <br><sub>`optional-fields`</sub> | fields marked `optional` | ✅ supported | `optional_and_arrays`, `type_refs`, `shapes`, `cross_schema`, `validators`, `validators_on_decode`, `large_fixed_arrays_nested` |
| arrays <br><sub>`arrays`</sub> | variable-length arrays, `T[]` | ✅ supported | `optional_and_arrays`, `type_refs`, `shapes`, `cross_schema`, `validators`, `validators_on_decode`, `large_fixed_arrays_nested` |
| fixed-length arrays <br><sub>`fixed-arrays`</sub> | fixed-length arrays, `T[N]` | 🟡 partial: rendered as `T[]`: the length isn't part of the type | `shapes`, `large_fixed_arrays_nested` |
| fixed arrays over 32 elements, nested <br><sub>`large-fixed-arrays-nested`</sub> | a `T[N]` with N over 32 anywhere but a field's own, non-optional type: inside another array, optional, an alias, an argument or a return | 🟡 partial: rendered as `T[]`: the length isn't part of the type | `large_fixed_arrays_nested` |
| unions <br><sub>`unions`</sub> | `union(A B ...)` types | ✅ supported | `unions` |
| type aliases <br><sub>`type-aliases`</sub> | `type Name = ...` declarations | ✅ supported | `validators`, `validators_on_decode`, `unions` |
| constants <br><sub>`constants`</sub> | `const` declarations | ✅ supported | `constant`, `shapes`, `validators`, `validators_on_decode` |
| protocols <br><sub>`protocols`</sub> | `protocol` declarations and their functions | ✅ supported | `protocol`, `error_shapes`, `validators`, `validators_on_decode`, `framing_jsonrpc`, `handshake_none`, `connections`, `connections_async`, `connections_jsonrpc`, `format_json` |
| errors <br><sub>`errors`</sub> | `error` declarations | ✅ supported | `protocol`, `error_shapes`, `format_json` |
| functions that throw <br><sub>`throws`</sub> | functions declared with `! Error` | ✅ supported | `protocol`, `error_shapes`, `format_json` |
| validators <br><sub>`validators`</sub> | `@validators` on fields and type aliases, checked in generated code | ⚪ ignored: the types are generated; the checks aren't run yet ([core#96](https://github.com/ComlineProject/core/issues/96)) | `validators`, `validators_on_decode` |
| imports between schemas <br><sub>`imports`</sub> | `use` of another schema's declarations | ✅ supported | `cross_schema`, `import_alias`, `import_glob`, `nested_namespace`, `external_std`, `validators`, `validators_on_decode` |
| nested namespaces <br><sub>`nested-namespaces`</sub> | schemas in subdirectories (`chat::admin`) | ✅ supported | `nested_namespace`, `external_std`, `validators`, `validators_on_decode` |
| `lib` mode <br><sub>`lib-mode`</sub> | `--mode lib`: a buildable package, not bare source files | ✅ supported | `nested_namespace`, `external_std` |
| `external_std` <br><sub>`external-std`</sub> | `[generate] external_std`: `std` referenced as its own package | ✅ supported | `external_std` |
| `validate_on_decode` <br><sub>`validate-on-decode`</sub> | `[generate] validate_on_decode`: decoding runs the checks | ⚪ ignored: no checks are generated to run on decode yet ([core#96](https://github.com/ComlineProject/core/issues/96)) | `validators_on_decode` |
| JSON-RPC framing <br><sub>`framing-jsonrpc`</sub> | `@framing = "jsonrpc"` (or as the package default) | ✅ supported | `framing_jsonrpc`, `connections_jsonrpc` |
| no handshake <br><sub>`handshake-none`</sub> | `@handshake = "none"` (or as the package default) | ✅ supported | `handshake_none` |
| connections <br><sub>`connections`</sub> | protocols on a connection, with calls in both directions: `datagram@2` (the default), or `@provider = Client` / `Multiple` | ✅ supported | `protocol`, `error_shapes`, `validators`, `validators_on_decode`, `handshake_none`, `connections`, `connections_async`, `connections_jsonrpc`, `format_json` |
| `async` <br><sub>`async`</sub> | `[generate] async`: connection protocols get async handlers and senders | ⚪ ignored: handlers and senders always return Promises: the output is async either way | `connections_async` |
| the `packed@1` format <br><sub>`format-packed`</sub> | `wire.format = "packed@1"`, the default: fixed-width fields, no tags | ✅ supported | `protocol`, `error_shapes`, `validators`, `validators_on_decode`, `handshake_none`, `connections`, `connections_async` |
| the `json@1` format <br><sub>`format-json`</sub> | `wire.format = "json@1"` | ✅ supported | `format_json` |
| the `msgpack@1` format <br><sub>`format-msgpack`</sub> | `wire.format = "msgpack@1"` | ❌ unsupported: `@comline/runtime` has no MessagePack codec yet | `format_msgpack` |

<!-- codegen:end -->

## Runtime

What the [`@comline/runtime`](https://github.com/ComlineProject/comline-typescript/tree/main/runtime) runtime speaks on the wire, proven against the
shared [wire corpus](https://github.com/ComlineProject/runtime/tree/main/runtime/conformance):
byte-exact examples of the handshake, the envelopes, each framing and each
wire format. The claims are in [`conformance-support.json`](https://github.com/ComlineProject/comline-typescript/blob/main/runtime/conformance-support.json).

<!-- runtime:start -->
<!-- Rendered from ComlineProject/runtime's conformance corpus and each runtime's report by scripts/sync-language-support.py - don't edit by hand. -->

Runtime `typescript`.

| Feature | What it covers | State | Proven by |
|---|---|---|---|
| name hash <br><sub>`name-hash`</sub> | FNV-1a 64 of a wire format or framing name, as the handshake carries it | ✅ supported | [8 cases](https://github.com/ComlineProject/runtime/blob/main/runtime/conformance/vectors/name-hash.json) |
| handshake <br><sub>`handshake`</sub> | the fixed 31-byte frame each side sends first: magic, version, IR hash, wire format, framing, capabilities | ✅ supported | [9 cases](https://github.com/ComlineProject/runtime/blob/main/runtime/conformance/vectors/handshake.json) |
| envelope <br><sub>`envelope`</sub> | a response's outcome: ok with a payload, an error ordinal with its body, or a provider fault | ✅ supported | [8 cases](https://github.com/ComlineProject/runtime/blob/main/runtime/conformance/vectors/envelope.json) |
| datagram framing <br><sub>`framing-datagram`</sub> | Comline's own binary framing of requests and responses | ✅ supported | [9 cases](https://github.com/ComlineProject/runtime/blob/main/runtime/conformance/vectors/framing-datagram.json) |
| datagram@2 framing <br><sub>`framing-datagram2`</sub> | the datagram framing with a request/reply kind and a protocol number, for calls in both directions and several protocols on one connection | ✅ supported | [12 cases](https://github.com/ComlineProject/runtime/blob/main/runtime/conformance/vectors/framing-datagram2.json) |
| JSON-RPC framing <br><sub>`framing-jsonrpc`</sub> | JSON-RPC 2.0 requests and responses, a fault as -32603 | ✅ supported | [19 cases](https://github.com/ComlineProject/runtime/blob/main/runtime/conformance/vectors/framing-jsonrpc.json) |
| JSON wire format <br><sub>`format-json`</sub> | values as UTF-8 JSON: a struct as an object | 🟡 partial: decoding doesn't check enum variants or integer ranges ([comline-typescript#57](https://github.com/ComlineProject/comline-typescript/issues/57)) <br>fails: `format-json/decode-unknown-variant`, `format-json/decode-wider-integer-overflow` | [44 cases](https://github.com/ComlineProject/runtime/blob/main/runtime/conformance/vectors/format-json.json) |
| MessagePack wire format <br><sub>`format-msgpack`</sub> | values as MessagePack: a struct as an array | ❌ unsupported: JSON and packed@1 ship | — |
| packed wire format <br><sub>`format-packed`</sub> | values as packed@1: fixed-width fields back to back, varint lengths, no tags | ✅ supported | [59 cases](https://github.com/ComlineProject/runtime/blob/main/runtime/conformance/vectors/format-packed.json) |

<!-- runtime:end -->

## Verification

The TypeScript runtime is also checked against the Rust reference on random
inputs, in addition to the vectors above. Its divergences from the reference are
tracked, each with the issue that will fix it.

### Differential properties

- [Property tests](https://github.com/ComlineProject/comline-typescript/tree/main/runtime/test/prop)
  (`fast-check`) run the same random types and values through this runtime and
  the `comline-reference` process, and compare what each encodes, accepts and
  refuses: the formats, the framings, the envelope and the handshake.
- Pull requests run a short suite; a nightly run takes 20,000 cases per
  property and opens an issue on a divergence outside the known classes.

The property suite doesn't write a results file, so there are no run counts to
show here. Coverage-guided fuzzing (Jazzer.js) isn't set up yet.

### Divergences

<!-- divergences:start -->
<!-- Rendered from each runtime's verification reports by scripts/sync-language-support.py - don't edit by hand. -->

Where `typescript` and the reference are known to answer differently, from [`known-divergences.json`](https://github.com/ComlineProject/comline-typescript/blob/main/runtime/known-divergences.json). The differential tests report a difference in one of these classes and fail on any other.

| Class | What differs | Issue |
|---|---|---|
| `json-decode-unchecked-variants-and-ranges` | json@1 decoding accepts a string that isn't one of the enum's variants, and an integer outside its type's range; the reference refuses both | [comline-typescript#57](https://github.com/ComlineProject/comline-typescript/issues/57) |
| `json-decode-unchecked-shape` | json@1 decoding accepts the wrong JSON kind, a missing or repeated struct field, an integer spelled 1.0, 1e0 or -0, and a float past its range; the reference refuses them | [comline-typescript#73](https://github.com/ComlineProject/comline-typescript/issues/73) |
| `json-encode-f32-digits` | json@1 writes an f32 with the shortest digits of a double (1.401298464324817e-45), the reference with those of the f32 (1e-45): the same f32, not the same JSON number | [comline-typescript#74](https://github.com/ComlineProject/comline-typescript/issues/74) |
| `jsonrpc-decode-lenient` | jsonrpc@1 decoding accepts a declared member twice, and an id or error code spelled 1.0, 1e0 or -0; the reference refuses both | [comline-typescript#75](https://github.com/ComlineProject/comline-typescript/issues/75) |
| `connection-replies-in-any-order` | Connection hands a reply to the call it answers in any order; an ordered (nested, blocking) Rust State refuses a reply that skips the innermost waiting call as a framing error. TypeScript has only the async model | [comline-typescript#77](https://github.com/ComlineProject/comline-typescript/issues/77) |

<!-- divergences:end -->

### Benchmarks

--8<-- "_generated/reports/typescript.bench.md"
