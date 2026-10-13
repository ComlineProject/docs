# Proposal C — syntax trees

Status: **under discussion** · One component recommended, the whole not · See
the [section overview](index.md) for the question all five answer

**The idea:** stop producing text directly. Build a real syntax tree for the
target language and let a printer render it, so syntactically invalid output
becomes impossible to express.

## Shape

For **Rust**, this is well supported and cheap:

```rust
// build a TokenStream, print it properly formatted
let item = quote! {
    #[derive(Serialize, Deserialize)]
    pub struct #name { #(#fields),* }
};
prettyplease::unparse(&syn::parse2(item)?)
```

`proc-macro2`, `syn`, `quote` and `prettyplease` are all pure Rust and
wasm-compatible. This is what `tonic-build` does.

For **TypeScript** there is no comparable native option. The realistic
choices are SWC's `swc_ecma_ast` + `swc_ecma_codegen`, or Biome's — both
large, both built for parsing and transforming real-world JavaScript rather
than constructing it, and both adding megabytes to a wasm bundle that
currently carries the compiler, the language server and both generators.

There is a **much cheaper subset** of this proposal worth separating out:
keep string building, then *parse and re-print* the result.

```rust
let text = /* existing push_str output */;
let file = syn::parse_file(&text)?;        // a parse failure is a generator bug
prettyplease::unparse(&file)               // canonical formatting, free
```

## The case for it

- **Malformed output becomes unrepresentable** for Rust — no missing comma, no
  unbalanced brace, no broken generic ever reaches a file.
- **Formatting stops being hand-managed.** Indentation, line wrapping and
  blank-line conventions come from the printer. No `\x20` escapes, no manual
  two-space strings.
- **The parse-then-print subset is nearly free and self-checking.** It needs
  no restructuring at all, and it converts "the generator emitted something
  that doesn't parse" from a silent user-facing bug into a generation-time
  error. Applied to the conformance corpus, it is a syntax guarantee for every
  fixture at essentially no cost.
- **`quote!` reads like the output.** For a Rust target it has much of
  [B](template-rendering.md)'s readability benefit with full type checking.

## The case against

- **It prevents the wrong bugs.** Every defect in the
  [overview's table](index.md#what-the-evidence-says) was *syntactically
  valid*: `req: Request` with no import parses perfectly and typechecks
  nowhere. A tree guarantees well-formedness, which was never the failure
  mode here.
- **It does not generalise past Rust.** Comline's second target is
  TypeScript, and the honest options there are heavy enough to threaten the
  wasm playground — the one hard constraint in
  [the overview](index.md#one-constraint-narrows-the-field). A strategy that
  works for one of two targets is not a strategy for building generators.
- **AST construction is verbose for generation.** These APIs are designed for
  *analysing* code. Constructing a large file node by node is wordier than the
  string building it replaces, and `quote!` only avoids that because Rust has
  macro-level quasi-quoting — TypeScript has no equivalent available from Rust.
- **For dynamic targets it is pointless.** A Lua or Python emitter gains
  almost nothing from an AST; there is barely any syntax to get wrong.

## Example projects

| Project | Trees? | Notes |
|---|---|---|
| **tonic-build** | yes (Rust only) | `quote!` + `prettyplease`; the model for the Rust half of this proposal |
| **prost-build** | no | string building, then optional `rustfmt`; the parse-then-print subset, essentially |
| **ts-morph / TypeScript factory API** | yes | excellent — but it is TypeScript, usable only from [Proposal D](target-language-plugins.md) |
| **Protocol Buffers' C++ generators** | no | `io::Printer` with `$var$` substitution: text with variables, closer to [B](template-rendering.md) |
| **smithy-rs** | no | writes text through a code writer, and relies on `rustfmt` plus compiling the output in CI |

Note what the mature generators actually do: they write text and then *check
it by compiling it*. That is the same conclusion the subset below reaches.

## When this would be the right call

The **parse-then-print subset is worth taking now**, independently of which
other proposal wins: it is a few lines in the Rust generator, pure Rust,
wasm-safe, and it turns syntax errors into generation-time failures.

The TypeScript equivalent of that check already exists in a better form — the
CI job that compiles `@comline/std` with `tsc`. Extending that to typecheck
the conformance corpus's generated output gives the same guarantee without
putting a JavaScript toolchain inside the generator.

Full AST-based emission would be the right call only if Comline's targets were
all statically typed *and* each had a mature, lightweight Rust AST builder.
That is true for Rust alone.
