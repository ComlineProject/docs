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
| structs <br><sub>`structs`</sub> | `struct` declarations | ✅ supported | `primitives`, `optional_and_arrays`, `type_refs`, `shapes`, `cross_schema`, `import_alias`, `import_glob`, `nested_namespace`, `external_std`, `validators`, `validators_on_decode`, `unions`, `large_fixed_arrays_nested` |
| enums <br><sub>`enums`</sub> | `enum` declarations | ✅ supported | `enum_basic` |
| optional fields <br><sub>`optional-fields`</sub> | fields marked `optional` | ✅ supported | `optional_and_arrays`, `type_refs`, `shapes`, `cross_schema`, `validators`, `validators_on_decode`, `large_fixed_arrays_nested` |
| arrays <br><sub>`arrays`</sub> | variable-length arrays, `T[]` | ✅ supported | `optional_and_arrays`, `type_refs`, `shapes`, `cross_schema`, `validators`, `validators_on_decode`, `large_fixed_arrays_nested` |
| fixed-length arrays <br><sub>`fixed-arrays`</sub> | fixed-length arrays, `T[N]` | 🟡 partial: rendered as `T[]`: the length isn't part of the type | `shapes`, `large_fixed_arrays_nested` |
| fixed arrays over 32 elements, nested <br><sub>`large-fixed-arrays-nested`</sub> | a `T[N]` with N over 32 anywhere but a field's own, non-optional type: inside another array, optional, an alias, an argument or a return | 🟡 partial: rendered as `T[]`: the length isn't part of the type | `large_fixed_arrays_nested` |
| unions <br><sub>`unions`</sub> | `union(A B ...)` types | ✅ supported | `unions` |
| type aliases <br><sub>`type-aliases`</sub> | `type Name = ...` declarations | ✅ supported | `validators`, `validators_on_decode`, `unions` |
| constants <br><sub>`constants`</sub> | `const` declarations | ✅ supported | `constant`, `shapes`, `validators`, `validators_on_decode` |
| protocols <br><sub>`protocols`</sub> | `protocol` declarations and their functions | ✅ supported | `protocol`, `error_shapes`, `validators`, `validators_on_decode`, `framing_jsonrpc` |
| errors <br><sub>`errors`</sub> | `error` declarations | ✅ supported | `protocol`, `error_shapes` |
| functions that throw <br><sub>`throws`</sub> | functions declared with `! Error` | ✅ supported | `protocol`, `error_shapes` |
| validators <br><sub>`validators`</sub> | `@validators` on fields and type aliases, checked in generated code | ⚪ ignored: the types are generated; the checks aren't run yet ([core#96](https://github.com/ComlineProject/core/issues/96)) | `validators`, `validators_on_decode` |
| imports between schemas <br><sub>`imports`</sub> | `use` of another schema's declarations | ✅ supported | `cross_schema`, `import_alias`, `import_glob`, `nested_namespace`, `external_std`, `validators`, `validators_on_decode` |
| nested namespaces <br><sub>`nested-namespaces`</sub> | schemas in subdirectories (`chat::admin`) | ✅ supported | `nested_namespace`, `external_std`, `validators`, `validators_on_decode` |
| `lib` mode <br><sub>`lib-mode`</sub> | `--mode lib`: a buildable package, not bare source files | ✅ supported | `nested_namespace`, `external_std` |
| `external_std` <br><sub>`external-std`</sub> | `[generate] external_std`: `std` referenced as its own package | ✅ supported | `external_std` |
| `validate_on_decode` <br><sub>`validate-on-decode`</sub> | `[generate] validate_on_decode`: decoding runs the checks | ⚪ ignored: no checks are generated to run on decode yet ([core#96](https://github.com/ComlineProject/core/issues/96)) | `validators_on_decode` |
| JSON-RPC framing <br><sub>`framing-jsonrpc`</sub> | `@framing = "jsonrpc"` (or as the package default) | ✅ supported | `framing_jsonrpc` |

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
| name hash <br><sub>`name-hash`</sub> | FNV-1a 64 of a wire format or framing name, as the handshake carries it | ✅ supported | [6 cases](https://github.com/ComlineProject/runtime/blob/main/runtime/conformance/vectors/name-hash.json) |
| handshake <br><sub>`handshake`</sub> | the fixed 31-byte frame each side sends first: magic, version, IR hash, wire format, framing, capabilities | ✅ supported | [7 cases](https://github.com/ComlineProject/runtime/blob/main/runtime/conformance/vectors/handshake.json) |
| envelope <br><sub>`envelope`</sub> | a response's outcome: ok with a payload, an error ordinal with its body, or a provider fault | ✅ supported | [8 cases](https://github.com/ComlineProject/runtime/blob/main/runtime/conformance/vectors/envelope.json) |
| datagram framing <br><sub>`framing-datagram`</sub> | Comline's own binary framing of requests and responses | ✅ supported | [9 cases](https://github.com/ComlineProject/runtime/blob/main/runtime/conformance/vectors/framing-datagram.json) |
| JSON-RPC framing <br><sub>`framing-jsonrpc`</sub> | JSON-RPC 2.0 requests and responses, a fault as -32603 | ✅ supported | [9 cases](https://github.com/ComlineProject/runtime/blob/main/runtime/conformance/vectors/framing-jsonrpc.json) |
| JSON wire format <br><sub>`format-json`</sub> | values as UTF-8 JSON: a struct as an object | 🟡 partial: 64-bit integers are `number`, exact only below 2^53 ([comline-typescript#49](https://github.com/ComlineProject/comline-typescript/issues/49)) <br>fails: `format-json/u64-above-2-53`, `format-json/u64-max`, `format-json/i64-min` | [21 cases](https://github.com/ComlineProject/runtime/blob/main/runtime/conformance/vectors/format-json.json) |
| MessagePack wire format <br><sub>`format-msgpack`</sub> | values as MessagePack: a struct as an array | ❌ unsupported: only JSON ships | — |

<!-- runtime:end -->
