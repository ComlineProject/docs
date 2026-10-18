# Languages

What Comline supports in each target language. Every language has its own
page, with what its **code generator** emits and, once runtime conformance
covers it, what its **runtime** speaks on the wire. The matrix below compares
the code generators side by side.

Nothing here is written by hand. Each entry comes from a conformance suite,
which checks the claim against what the generator actually does, so a
language page can't claim something that isn't true.

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

## Code generation, side by side

<!-- matrix:start -->
<!-- Rendered from ComlineProject/generation's features.json by scripts/sync-language-support.py - don't edit by hand. -->

| Feature | [rust 1.70.0](rust.md) | [typescript 5.0](typescript.md) |
|---|---|---|
| structs <br><sub>`structs`</sub> | ✅ supported | ✅ supported |
| enums <br><sub>`enums`</sub> | ✅ supported | ✅ supported |
| optional fields <br><sub>`optional-fields`</sub> | ✅ supported | ✅ supported |
| arrays <br><sub>`arrays`</sub> | ✅ supported | ✅ supported |
| fixed-length arrays <br><sub>`fixed-arrays`</sub> | ✅ supported | 🟡 partial: rendered as `T[]`: the length isn't part of the type |
| fixed arrays over 32 elements, nested <br><sub>`large-fixed-arrays-nested`</sub> | ❌ unsupported: a fixed array over 32 elements renders only as a struct or error field's own, non-optional type (serde's derive stops at 32) | 🟡 partial: rendered as `T[]`: the length isn't part of the type |
| unions <br><sub>`unions`</sub> | ❌ unsupported: Rust has no anonymous sum type to render one as | ✅ supported |
| type aliases <br><sub>`type-aliases`</sub> | ✅ supported | ✅ supported |
| constants <br><sub>`constants`</sub> | ✅ supported | ✅ supported |
| protocols <br><sub>`protocols`</sub> | ✅ supported | ✅ supported |
| errors <br><sub>`errors`</sub> | ✅ supported | ✅ supported |
| functions that throw <br><sub>`throws`</sub> | ✅ supported | ✅ supported |
| validators <br><sub>`validators`</sub> | ✅ supported | ⚪ ignored: the types are generated; the checks aren't run yet ([core#96](https://github.com/ComlineProject/core/issues/96)) |
| imports between schemas <br><sub>`imports`</sub> | ✅ supported | ✅ supported |
| nested namespaces <br><sub>`nested-namespaces`</sub> | ✅ supported | ✅ supported |
| `lib` mode <br><sub>`lib-mode`</sub> | ✅ supported | ✅ supported |
| `external_std` <br><sub>`external-std`</sub> | ✅ supported | ✅ supported |
| `validate_on_decode` <br><sub>`validate-on-decode`</sub> | ✅ supported | ⚪ ignored: no checks are generated to run on decode yet ([core#96](https://github.com/ComlineProject/core/issues/96)) |
| JSON-RPC framing <br><sub>`framing-jsonrpc`</sub> | ✅ supported | ✅ supported |

<!-- matrix:end -->

## Elsewhere

- `comline targets --features` prints the code generation support for the
  generators your `comline` was built with, and `--json` prints it as JSON (see
  the [CLI](../cli.md)).
- In the editor, a schema using a feature that a language declared in
  `config.idp` can't generate gets a warning at the use. Hovering the language
  in `config.idp` shows what its generator supports.
- Each generator's repository README carries its own table:
  [comline-rust](https://github.com/ComlineProject/comline-rust#features),
  [comline-typescript](https://github.com/ComlineProject/comline-typescript#features).
