# How generators are built

**The question.** Every Comline generator today is hand-written Rust that
pushes strings: `generate_rust` and `generate_typescript` are 1,120 and 1,083
lines of `push_str` over frozen IR. That was a proof of concept, not a
commitment. Should generation keep that shape, move to templates, move to
syntax trees, move out of Rust entirely — or stop being Comline's job at all?

Five proposals answer it, written to the same shape so they can be read side
by side.

| | Approach | In one line | Assessment |
|---|---|---|---|
| [Proposal A](resolution-kernel.md) | **Shared resolution kernel** | a symbol/module layer in `comline-codegen`; generators map a resolved model to syntax | **recommended** |
| [Proposal B](template-rendering.md) | **Templates** | per-language template files replace `push_str` | complementary to A, not a substitute |
| [Proposal C](syntax-tree-emission.md) | **Syntax trees** | build a real AST per target and pretty-print it | narrow value; one cheap piece worth taking |
| [Proposal D](target-language-plugins.md) | **Target-language plugins** | `protoc`-style: each generator is a program in its own language | blocked by a current constraint |
| [Proposal E](adopt-existing-model.md) | **Adopt an existing model** | translate Comline IR to Smithy/protobuf and inherit their generators | assessed, not recommended |

## What the evidence says

The question is usually framed as *how should output be spelled* — strings,
templates, or trees. Comline's own defect history says that is the wrong axis.

Every generation bug found so far was a **missing-model** bug:

| Defect | Cause |
|---|---|
| Cross-schema references emitted as bare names with no imports — fixed in `comline-rust#28`, then **independently again** in `comline-typescript#32` | no symbol resolution |
| `use ns::Name as Alias` resolving to `crate::ns::Alias` (still live in the Rust generator) | no symbol resolution |
| `error_type_names` same-file-only in **both** generators, falling back to `UnknownError<n>` | no cross-schema lookup |
| `ModuleTree` and `NamespaceTree` written twice, each refusing different things | no shared module model |
| Framing selection drifting across three implementations until centralised in `annotations::canonical_value` | duplicated knowledge |
| `map_str_type`, manifest dependency logic, and `external_std` filtering each written twice | duplicated knowledge |

Now test each approach against that list. **Templates would have prevented
none of them.** **Syntax trees would have prevented none of them** — a field
typed `Request` with no import is syntactically perfect TypeScript. Those
tools prevent malformed output; every defect above was well-formed and
semantically wrong.

What prevents them is a layer that knows where a symbol comes from and records
the dependency when you name it. That layer was hand-rolled twice already, as
`build_import_map` plus a used-name set.

**The safety net is shaped wrong, too.** `conformance::Fixture` is *one
schema* and one namespace, so the corpus cannot express a cross-schema
reference at all — which is why the same bug shipped twice under a green test
suite.

**The marginal cost of a language is the other symptom.** `generation/lib-gen`
holds four abandoned starts — `c`, `lua`, `luau`, `python`, between 3 and 108
lines. Adding a target currently means re-deriving module trees, import
resolution, primitive maps and manifest emission by hand. Nobody finished.

## One constraint narrows the field

`playground/wasm` compiles the generators to **wasm32 and runs them in the
browser**, deliberately: its manifest says the playground runs *that* code,
"not a re-implementation."

That is what blocks [Proposal D](target-language-plugins.md), otherwise the
strongest strategic option — it would let a TypeScript developer write the
TypeScript generator with TypeScript's own tooling, and would retire the
git-rev pin cascade across seven repositories. It also rules out heavyweight
AST toolchains in [C](syntax-tree-emission.md) and kills
[E](adopt-existing-model.md), whose toolchains are JVM-based.

Two facts make the remaining options cheaper than they look: **Handlebars is
already a dependency of `comline-core`** (`utils/templating.rs`, used for
`layout`) and therefore already proven under wasm; and `syn` + `prettyplease`
are pure Rust, so Rust output could be parsed and re-printed for free
formatting *and* a syntax-validity check.

## The recommendation

Take [A](resolution-kernel.md), and take it in two steps — the corpus first,
because it both proves the diagnosis and guards the refactor that follows.
[B](template-rendering.md) becomes cheap and safe afterwards and can be
decided on its own merits; the formatter half of [C](syntax-tree-emission.md)
is worth taking regardless. Keep [D](target-language-plugins.md) reachable by
keeping the kernel's request boundary serialisable — core already speaks CBOR
— rather than by building it now.
