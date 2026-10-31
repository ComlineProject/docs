# Proposal A — a shared resolution kernel

Status: **implemented** · shipped as `symbols`, `modules`, `stdlib` and `naming` in
`comline-codegen` (see [What shipped](index.md#what-shipped)) · See the
[section overview](index.md) for the question all five answer · Complemented
by, not opposed to, [Proposal B — templates](template-rendering.md)

**The idea:** keep generators in Rust, but stop making each one re-derive what
a name *means*. `comline-codegen` grows from a 175-line contract into a kernel
that resolves the frozen IR into a target-neutral model — symbols with known
origins, a module tree, dependency edges — and a writer that records an import
when you name a type. A generator then only maps that model to syntax.

## Shape

```
comline-codegen/
  contract.rs     GenRequest, GeneratedFile, Mode, Registry   (today's 175 lines)
  symbols.rs      SymbolProvider: bare name -> origin + declared name,
                  with aliases, globs and error ordinals resolved once
  modules.rs      ModuleTree parameterised by target conventions
                  (file-per-namespace vs barrel, reserved roots, separator)
  writer.rs       Writer: naming a symbol registers its dependency;
                  the import/use block emits itself
  manifest.rs     dependency declaration helpers (a package, a version or
                  rev, "declare only if actually referenced")
  naming.rs       pascal / camel / screaming_snake, collision-free
```

The per-language crates keep their own repos and their own `register()`, and
shrink to what is genuinely language-specific: primitive mapping, syntax
templates, manifest format, and the conventions they pass to `ModuleTree`.

The sequencing matters:

1. **Multi-schema conformance first.** `conformance::Fixture` becomes a
   *package* of schemas rather than one schema. The corpus can then express a
   cross-schema reference, an alias, a glob, a nested namespace and an
   external-std reference — none of which it can express today.
2. **Extract the kernel**, one concern at a time, with the Rust and TypeScript
   generators as the two consumers that prove each piece generalises.
3. **Retire the duplicates**: `build_import_map` ×2, `ModuleTree` /
   `NamespaceTree`, `map_str_type` ×2, `error_type_names` ×2, the
   `external_std` filter ×2.

## The case for it

- **It targets the defects that actually happened.** Every bug in the
  [overview's table](index.md#what-the-evidence-says) is a resolution bug.
  Import registration as a side effect of naming a symbol makes the
  bare-name class unrepresentable rather than merely fixed twice.
- **It fixes the duplication that is already load-bearing.** Three of this
  group's concerns were written twice *in the same week* — the module tree, the
  import map, the `external_std` filter. The second copy is written by
  transcribing the first, which is exactly how the alias bug survived in Rust
  while TypeScript got it right.
- **It lowers the marginal cost of a language**, which is the standing
  blocker: four `lib-gen` starts died at under 110 lines each. A generator
  that doesn't have to invent module resolution is a weekend, not a quarter.
- **No new dependencies and no constraint violations.** Pure Rust, wasm-safe,
  single binary, no toolchain at generate time — it keeps every property the
  current design has, including the playground running the real generators.
- **Incremental and reversible.** Each extraction is a refactor with two
  consumers and a golden corpus either side of it. There is no flag day.

## The case against

- **It is the least visible option.** It produces no new capability and no
  nicer-looking source; the win is bugs that never happen and languages that
  become cheap later. That is a hard thing to prioritise.
- **It is a guess about generality from two samples.** Rust and TypeScript are
  both statically typed with module systems and manifests. A dynamic target
  (Lua, Python) may want much less, and a C target much more — the kernel
  could end up with conventions that fit nobody when the third and fourth
  languages arrive.
- **Abstraction can outrun the evidence.** `ModuleTree` and `NamespaceTree`
  were deliberately *not* unified when `lib` mode landed in TypeScript,
  precisely because one type covering both looked like two implementations
  behind one name. That judgement has to be revisited honestly, not assumed
  away: the shared version must be parameterised by real differences, not by
  every difference.
- **It does nothing about the pin cascade**, the other recurring cost, which
  only [D](target-language-plugins.md) or publishing addresses.

## Example projects

| Project | Kernel? | What it looks like |
|---|---|---|
| **smithy-rs** | yes | `SymbolProvider` maps model shapes to target symbols; `RustWriter` registers a dependency when a symbol is used and emits the `use` block itself — the direct precedent for this proposal |
| **quicktype** | yes | a shared `Renderer` plus a `Namer` that handles naming conventions and collision avoidance across ~20 targets; per-target code is small |
| **wit-bindgen** | yes | `wit-bindgen-core` holds the traversal and shared concerns; each language is a thin bindgen crate |
| **Apache Thrift** | no | a hand-written emitter per language in the C++ compiler; the canonical example of per-language duplication and divergent feature support |
| **Protocol Buffers** | partial | descriptor resolution is shared and thorough, but each plugin re-implements its own naming and import strategy |

The pattern: projects that reached many targets have a kernel. Projects that
grew emitters per language either stayed small or ended up with uneven
language support — which is the shape `lib-gen`'s four stubs already have.

## When this would be the right call

When the intent is to support more than two or three targets, and when the
bugs being hit are about *meaning* rather than *appearance*. Both hold here.

It would be the wrong call if Comline were settling on exactly two
first-class targets forever, or if the generators' defects were
formatting-shaped — in which case [B](template-rendering.md) alone would do.
