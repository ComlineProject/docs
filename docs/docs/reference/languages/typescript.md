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

Not yet covered by conformance. Runtime conformance checks each runtime against
shared, byte-exact wire examples (the handshake, the envelopes, each framing
and each wire format). This section lists the result once it covers TypeScript.
