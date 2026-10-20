# Languages

What Comline supports in each target language. Every language has its own
page, with what its **code generator** emits and what its **runtime** speaks
on the wire. The matrices below compare the languages side by side.

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

A runtime's claims use the same words, about the wire:

| State | The runtime, for that wire feature |
|---|---|
| ✅ **supported** | Reproduces every example in the wire corpus, and decodes each back. |
| 🟡 **partial** | Does the same, except for the examples the note lists, which it's known to get wrong. |
| ❌ **unsupported** | Doesn't implement it. A peer must agree on something else at the handshake. |

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

Runtimes are proven against a shared wire corpus in
[`ComlineProject/runtime`](https://github.com/ComlineProject/runtime/tree/main/runtime/conformance):
for each wire feature, examples of exact bytes and the input that produces
them, plus bytes that must be refused. The Rust runtime is the reference that
the examples are taken from; every other runtime vendors them at a pinned
commit. A runtime's suite runs every example against it:

- **supported**: every example encodes to its bytes and decodes back, and
  every malformed one is refused. JSON compares as JSON, with numbers exact,
  so `1` and `1.0` are equal but a rounded large integer isn't.
- **partial**: as for supported, except for the listed examples, which must
  still fail. When one starts passing, the suite fails until the claim is
  upgraded.
- **unsupported**: the runtime reports every example as not implemented.

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

## Runtimes, side by side

<!-- runtime-matrix:start -->
<!-- Rendered from ComlineProject/runtime's conformance corpus and each runtime's report by scripts/sync-language-support.py - don't edit by hand. -->

| Feature | [rust](rust.md#runtime) | [typescript](typescript.md#runtime) |
|---|---|---|
| name hash <br><sub>`name-hash`</sub> | ✅ supported | ✅ supported |
| handshake <br><sub>`handshake`</sub> | ✅ supported | ✅ supported |
| envelope <br><sub>`envelope`</sub> | ✅ supported | ✅ supported |
| datagram framing <br><sub>`framing-datagram`</sub> | ✅ supported | ✅ supported |
| JSON-RPC framing <br><sub>`framing-jsonrpc`</sub> | ✅ supported | ✅ supported |
| JSON wire format <br><sub>`format-json`</sub> | ✅ supported | 🟡 partial: decoding doesn't check enum variants or integer ranges ([comline-typescript#57](https://github.com/ComlineProject/comline-typescript/issues/57)) |
| MessagePack wire format <br><sub>`format-msgpack`</sub> | ✅ supported | ❌ unsupported: only JSON ships |

<!-- runtime-matrix:end -->

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
