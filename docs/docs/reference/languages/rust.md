# Rust

What Comline supports in Rust, as its conformance suites prove it. For how
to use it, see the [Rust guide](../../languages/rust/index.md). The states are explained in the
[overview](index.md#what-the-states-mean).

## Code generation

What the [`comline-rust`](https://github.com/ComlineProject/comline-rust) generator emits
for each language feature, and the conformance fixtures that prove it.

<!-- codegen:start -->
<!-- Rendered from ComlineProject/generation's features.json by scripts/sync-language-support.py - don't edit by hand. -->

Generator `rust#1.70.0`.

| Feature | What it covers | State | Proven by |
|---|---|---|---|
| structs <br><sub>`structs`</sub> | `struct` declarations | ✅ supported | `primitives`, `optional_and_arrays`, `type_refs`, `protocol`, `shapes`, `cross_schema`, `import_alias`, `import_glob`, `nested_namespace`, `external_std`, `validators`, `validators_on_decode` |
| enums <br><sub>`enums`</sub> | `enum` declarations | ✅ supported | `enum_basic` |
| optional fields <br><sub>`optional-fields`</sub> | fields marked `optional` | ✅ supported | `optional_and_arrays`, `type_refs`, `shapes`, `cross_schema`, `validators`, `validators_on_decode` |
| arrays <br><sub>`arrays`</sub> | variable-length arrays, `T[]` | ✅ supported | `optional_and_arrays`, `type_refs`, `shapes`, `cross_schema`, `validators`, `validators_on_decode` |
| fixed-length arrays <br><sub>`fixed-arrays`</sub> | fixed-length arrays, `T[N]` | ✅ supported | `shapes` |
| fixed arrays over 32 elements, nested <br><sub>`large-fixed-arrays-nested`</sub> | a `T[N]` with N over 32 anywhere but a field's own, non-optional type: inside another array, optional, an alias, an argument or a return | ❌ unsupported: a fixed array over 32 elements renders only as a struct or error field's own, non-optional type (serde's derive stops at 32) | `large_fixed_arrays_nested` |
| unions <br><sub>`unions`</sub> | `union(A B ...)` types | ❌ unsupported: Rust has no anonymous sum type to render one as | `unions` |
| type aliases <br><sub>`type-aliases`</sub> | `type Name = ...` declarations | ✅ supported | `validators`, `validators_on_decode` |
| constants <br><sub>`constants`</sub> | `const` declarations | ✅ supported | `constant`, `shapes`, `validators`, `validators_on_decode` |
| protocols <br><sub>`protocols`</sub> | `protocol` declarations and their functions | ✅ supported | `protocol`, `error_shapes`, `validators`, `validators_on_decode`, `framing_jsonrpc`, `handshake_none`, `connections` |
| errors <br><sub>`errors`</sub> | `error` declarations | ✅ supported | `protocol`, `error_shapes` |
| functions that throw <br><sub>`throws`</sub> | functions declared with `! Error` | ✅ supported | `protocol`, `error_shapes` |
| validators <br><sub>`validators`</sub> | `@validators` on fields and type aliases, checked in generated code | ✅ supported | `validators`, `validators_on_decode` |
| imports between schemas <br><sub>`imports`</sub> | `use` of another schema's declarations | ✅ supported | `cross_schema`, `import_alias`, `import_glob`, `nested_namespace`, `external_std`, `validators`, `validators_on_decode` |
| nested namespaces <br><sub>`nested-namespaces`</sub> | schemas in subdirectories (`chat::admin`) | ✅ supported | `nested_namespace`, `external_std`, `validators`, `validators_on_decode` |
| `lib` mode <br><sub>`lib-mode`</sub> | `--mode lib`: a buildable package, not bare source files | ✅ supported | `nested_namespace`, `external_std` |
| `external_std` <br><sub>`external-std`</sub> | `[generate] external_std`: `std` referenced as its own package | ✅ supported | `external_std` |
| `validate_on_decode` <br><sub>`validate-on-decode`</sub> | `[generate] validate_on_decode`: decoding runs the checks | ✅ supported | `validators_on_decode` |
| JSON-RPC framing <br><sub>`framing-jsonrpc`</sub> | `@framing = "jsonrpc"` (or as the package default) | ✅ supported | `framing_jsonrpc` |
| no handshake <br><sub>`handshake-none`</sub> | `@handshake = "none"` (or as the package default) | ✅ supported | `handshake_none` |
| connections <br><sub>`connections`</sub> | protocols on a connection, with calls in both directions: `@framing = "datagram@2"`, or `@provider = Client` / `Multiple` | 🟡 partial: over `datagram@2`; JSON-RPC on a connection isn't supported yet ([runtime#19](https://github.com/ComlineProject/runtime/issues/19)) | `connections` |

<!-- codegen:end -->

## Runtime

What the [`comline-runtime`](https://github.com/ComlineProject/runtime) runtime speaks on the wire, proven against the
shared [wire corpus](https://github.com/ComlineProject/runtime/tree/main/runtime/conformance):
byte-exact examples of the handshake, the envelopes, each framing and each
wire format. The claims are in [`rust.json`](https://github.com/ComlineProject/runtime/blob/main/runtime/conformance/support/rust.json).

<!-- runtime:start -->
<!-- Rendered from ComlineProject/runtime's conformance corpus and each runtime's report by scripts/sync-language-support.py - don't edit by hand. -->

Runtime `rust`.

| Feature | What it covers | State | Proven by |
|---|---|---|---|
| name hash <br><sub>`name-hash`</sub> | FNV-1a 64 of a wire format or framing name, as the handshake carries it | ✅ supported | [7 cases](https://github.com/ComlineProject/runtime/blob/main/runtime/conformance/vectors/name-hash.json) |
| handshake <br><sub>`handshake`</sub> | the fixed 31-byte frame each side sends first: magic, version, IR hash, wire format, framing, capabilities | ✅ supported | [8 cases](https://github.com/ComlineProject/runtime/blob/main/runtime/conformance/vectors/handshake.json) |
| envelope <br><sub>`envelope`</sub> | a response's outcome: ok with a payload, an error ordinal with its body, or a provider fault | ✅ supported | [8 cases](https://github.com/ComlineProject/runtime/blob/main/runtime/conformance/vectors/envelope.json) |
| datagram framing <br><sub>`framing-datagram`</sub> | Comline's own binary framing of requests and responses | ✅ supported | [9 cases](https://github.com/ComlineProject/runtime/blob/main/runtime/conformance/vectors/framing-datagram.json) |
| datagram@2 framing <br><sub>`framing-datagram2`</sub> | the datagram framing with a request/reply kind and a protocol number, for calls in both directions and several protocols on one connection | ✅ supported | [12 cases](https://github.com/ComlineProject/runtime/blob/main/runtime/conformance/vectors/framing-datagram2.json) |
| JSON-RPC framing <br><sub>`framing-jsonrpc`</sub> | JSON-RPC 2.0 requests and responses, a fault as -32603 | ✅ supported | [9 cases](https://github.com/ComlineProject/runtime/blob/main/runtime/conformance/vectors/framing-jsonrpc.json) |
| JSON wire format <br><sub>`format-json`</sub> | values as UTF-8 JSON: a struct as an object | ✅ supported | [31 cases](https://github.com/ComlineProject/runtime/blob/main/runtime/conformance/vectors/format-json.json) |
| MessagePack wire format <br><sub>`format-msgpack`</sub> | values as MessagePack: a struct as an array | ✅ supported | [31 cases](https://github.com/ComlineProject/runtime/blob/main/runtime/conformance/vectors/format-msgpack.json) |

<!-- runtime:end -->
