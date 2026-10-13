# Proposal B — templates

Status: **under discussion** · Complementary to
[Proposal A](resolution-kernel.md) rather than competing with it · See the
[section overview](index.md) for the question all five answer

**The idea:** stop assembling output with `push_str` and move the shape of
generated source into template files, one set per language. The generator
becomes "build a context, render a template."

## Shape

```
comline-typescript/codegen/
  src/generator.rs        builds the render context from frozen IR
  templates/
    schema.ts.hbs         interfaces, enums, error classes
    protocol.ts.hbs       client, dispatcher, serve helper
    package.json.hbs      the lib-mode manifest
    tsconfig.json.hbs
```

Two credible engines, both already viable here:

- **Handlebars** — *already a dependency of `comline-core`*
  (`utils/templating.rs`, used for `layout`), so it is already proven under
  wasm. Runtime-loaded or `include_str!`-embedded; logic-light by design.
- **Askama / Rinja** — compile-time templates that become Rust code. Type-checked
  against their context struct, zero runtime, smallest wasm footprint, and a
  broken template fails `cargo build` rather than a generation run.

## The case for it

- **It removes the real ugliness.** The TypeScript generator is littered with
  `\x20` escapes and `\`-continued string literals to keep indentation
  readable inside Rust source. That is a tax on every edit, and templates
  remove it entirely — what the output looks like becomes visible in a file
  shaped like the output.
- **Non-Rust contributors can help.** Someone who knows idiomatic TypeScript
  but not Rust can fix emitted TypeScript. Today that requires reading
  1,083 lines of Rust that pushes strings. This is the single biggest
  contributor-accessibility win available short of
  [D](target-language-plugins.md).
- **Diffs become reviewable.** A change to emitted syntax shows up as a diff
  of the thing being emitted, not as a diff of the code that assembles it.
- **Askama keeps every current property.** Compile-time, no runtime
  dependency, wasm-safe, and strictly more checking than today.

## The case against

- **It fixes none of the defects.** This is the decisive point. Not one entry
  in the [overview's defect table](index.md#what-the-evidence-says) would have
  been prevented: templates change how output is spelled, not what the
  generator knows about a name's origin. Adopting B *instead of*
  [A](resolution-kernel.md) would leave the entire demonstrated bug class in
  place while feeling like progress.
- **Logic migrates into templates.** Every template system that reaches real
  codegen accumulates conditionals and loops until the template is a program
  in a worse language — OpenAPI Generator's Mustache templates are the
  cautionary case. Resisting that needs the context to be pre-computed, which
  is [A](resolution-kernel.md)'s job: the context struct *is* the resolved
  model.
- **Two places to debug.** A wrong character could be in the template or in
  the context. Handlebars errors are especially poor at saying which.
- **Order of operations matters.** Templating first would mean writing
  templates against today's unresolved context, then rewriting them when the
  context becomes a resolved model. Doing it after A means writing them once.

## Example projects

| Project | Templates? | Outcome |
|---|---|---|
| **OpenAPI Generator** | Mustache, ~100 generators | reached enormous language coverage; widely criticised for template-embedded logic and inconsistent output quality between targets |
| **swagger-codegen** | Mustache | same lineage, same trade-off |
| **sqlc, ent** | Go `text/template` | works well — context is fully resolved in Go before rendering, so templates stay dumb |
| **prost / tonic** | no | string building and `quote!` respectively; both stayed small enough not to need it |
| **smithy-rs** | no | an `AbstractCodeWriter` with inline formatting instead, so dependency tracking can be a side effect of writing |

The projects where templates work well are the ones that resolve everything
*before* rendering. The projects where templates went wrong are the ones that
asked templates to do the resolving.

## When this would be the right call

Immediately after [A](resolution-kernel.md), when there is a resolved context
to render and templates can stay logic-free. Askama is the better fit of the
two engines for Comline, since it preserves the compile-time, no-runtime,
wasm-safe properties the current design depends on — Handlebars' only
advantage is already being in the dependency graph.

It would be the wrong call as a substitute for A, or before it.
