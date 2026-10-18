# Generator support

What each code generator implements, feature by feature. The table below is
the one the generators' conformance suite produces, so every entry in it has
been checked, not just claimed.

## What the states mean

| State | Generating a schema that uses the feature |
|---|---|
| ✅ **supported** | Works. |
| 🟡 **partial** | Works, with the limit the note states. |
| ⚪ **ignored** | Succeeds, but the output is what it would be without the feature: the types are right, the feature has no effect. `comline generate` warns, and so does the editor. |
| ❌ **unsupported** | Is refused, with an error naming every use. The editor warns at each use. |

## How a claim is proven

Each generator states its support in a `SUPPORT` table in its own crate. The
conformance suite in
[`ComlineProject/generation`](https://github.com/ComlineProject/generation)
runs every generator over a corpus of schemas and checks each claim against
what the generator actually does:

- **supported** or **partial**: a schema in the corpus uses the feature,
  generates, and matches its checked-in output. Where the feature can be taken
  out of the schema, the output must change without it; otherwise the feature
  is really being ignored.
- **ignored**: the output is identical with the feature taken out, apart from
  the IR hash, which names the schema.
- **unsupported**: every schema using the feature is refused, with an error
  naming the feature.

A claim that no schema in the corpus can back fails the suite. So a new
feature, or a generator that gains one, comes with a schema that proves it.
The proving schemas are named in each cell below.

## The matrix

<!-- features:start -->
<!-- Copied from ComlineProject/generation's FEATURES.md by scripts/sync-generator-support.py - don't edit by hand. -->

| Feature | rust 1.70.0 | typescript 5.0 |
|---|---|---|
| structs <br><sub>`structs`</sub> | ✅ supported <br><sub>proven by `primitives`, `optional_and_arrays`, `type_refs` +8 more</sub> | ✅ supported <br><sub>proven by `primitives`, `optional_and_arrays`, `type_refs` +10 more</sub> |
| enums <br><sub>`enums`</sub> | ✅ supported <br><sub>proven by `enum_basic`</sub> | ✅ supported <br><sub>proven by `enum_basic`</sub> |
| optional fields <br><sub>`optional-fields`</sub> | ✅ supported <br><sub>proven by `optional_and_arrays`, `type_refs`, `shapes` +3 more</sub> | ✅ supported <br><sub>proven by `optional_and_arrays`, `type_refs`, `shapes` +4 more</sub> |
| arrays <br><sub>`arrays`</sub> | ✅ supported <br><sub>proven by `optional_and_arrays`, `type_refs`, `shapes` +3 more</sub> | ✅ supported <br><sub>proven by `optional_and_arrays`, `type_refs`, `shapes` +4 more</sub> |
| fixed-length arrays <br><sub>`fixed-arrays`</sub> | ✅ supported <br><sub>proven by `shapes`</sub> | 🟡 partial: rendered as `T[]`: the length isn't part of the type <br><sub>proven by `shapes`, `large_fixed_arrays_nested`</sub> |
| fixed arrays over 32 elements, nested <br><sub>`large-fixed-arrays-nested`</sub> | ❌ unsupported: a fixed array over 32 elements renders only as a struct or error field's own, non-optional type (serde's derive stops at 32) <br><sub>proven by `large_fixed_arrays_nested`</sub> | 🟡 partial: rendered as `T[]`: the length isn't part of the type <br><sub>proven by `large_fixed_arrays_nested`</sub> |
| unions <br><sub>`unions`</sub> | ❌ unsupported: Rust has no anonymous sum type to render one as <br><sub>proven by `unions`</sub> | ✅ supported <br><sub>proven by `unions`</sub> |
| type aliases <br><sub>`type-aliases`</sub> | ✅ supported <br><sub>proven by `validators`, `validators_on_decode`</sub> | ✅ supported <br><sub>proven by `validators`, `validators_on_decode`, `unions`</sub> |
| constants <br><sub>`constants`</sub> | ✅ supported <br><sub>proven by `constant`, `shapes`, `validators` +1 more</sub> | ✅ supported <br><sub>proven by `constant`, `shapes`, `validators` +1 more</sub> |
| protocols <br><sub>`protocols`</sub> | ✅ supported <br><sub>proven by `protocol`, `error_shapes`, `validators` +2 more</sub> | ✅ supported <br><sub>proven by `protocol`, `error_shapes`, `validators` +2 more</sub> |
| errors <br><sub>`errors`</sub> | ✅ supported <br><sub>proven by `protocol`, `error_shapes`</sub> | ✅ supported <br><sub>proven by `protocol`, `error_shapes`</sub> |
| functions that throw <br><sub>`throws`</sub> | ✅ supported <br><sub>proven by `protocol`, `error_shapes`</sub> | ✅ supported <br><sub>proven by `protocol`, `error_shapes`</sub> |
| validators <br><sub>`validators`</sub> | ✅ supported <br><sub>proven by `validators`, `validators_on_decode`</sub> | ⚪ ignored: the types are generated; the checks aren't run yet ([core#96](https://github.com/ComlineProject/core/issues/96)) <br><sub>proven by `validators`, `validators_on_decode`</sub> |
| imports between schemas <br><sub>`imports`</sub> | ✅ supported <br><sub>proven by `cross_schema`, `import_alias`, `import_glob` +4 more</sub> | ✅ supported <br><sub>proven by `cross_schema`, `import_alias`, `import_glob` +4 more</sub> |
| nested namespaces <br><sub>`nested-namespaces`</sub> | ✅ supported <br><sub>proven by `nested_namespace`, `external_std`, `validators` +1 more</sub> | ✅ supported <br><sub>proven by `nested_namespace`, `external_std`, `validators` +1 more</sub> |
| `lib` mode <br><sub>`lib-mode`</sub> | ✅ supported <br><sub>proven by `nested_namespace`, `external_std`</sub> | ✅ supported <br><sub>proven by `nested_namespace`, `external_std`</sub> |
| `external_std` <br><sub>`external-std`</sub> | ✅ supported <br><sub>proven by `external_std`</sub> | ✅ supported <br><sub>proven by `external_std`</sub> |
| `validate_on_decode` <br><sub>`validate-on-decode`</sub> | ✅ supported <br><sub>proven by `validators_on_decode`</sub> | ⚪ ignored: no checks are generated to run on decode yet ([core#96](https://github.com/ComlineProject/core/issues/96)) <br><sub>proven by `validators_on_decode`</sub> |
| JSON-RPC framing <br><sub>`framing-jsonrpc`</sub> | ✅ supported <br><sub>proven by `framing_jsonrpc`</sub> | ✅ supported <br><sub>proven by `framing_jsonrpc`</sub> |

<!-- features:end -->

## Elsewhere

- `comline targets --features` prints this for the generators your `comline`
  was built with, and `--json` prints it as JSON (see the [CLI](cli.md)).
- In the editor, a schema using a feature a language declared in `config.idp`
  can't generate gets a warning at the use. Hovering the language in
  `config.idp` shows what its generator supports.
- Each generator's repository README carries its own column:
  [comline-rust](https://github.com/ComlineProject/comline-rust#features),
  [comline-typescript](https://github.com/ComlineProject/comline-typescript#features).
