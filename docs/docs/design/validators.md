# Validators

Status: **parses and freezes** (core#32, #33, #34) · **not enforced** ·
resolution + runtime checks are phases 3–4

A **validator** is a named, parameterised check attached to a
[struct](../guide/idl/structure.md) or [error](../guide/idl/error.md) field. The
declaration, its `validate` block, and the `@validators` field annotation all
parse today and are recorded in the IR — nothing acts on them yet.

## Shape

### The `validator` declaration

```
/// Checks a string's length is within bounds.
/// @min_chars: minimum length
/// @max_chars: maximum length
validator StringBounds {
    min_chars: u32 = 0
    max_chars: u32 = 1024

    validate {
        assert(value.length >= params.min_chars,
               "{value.name} must be at least {params.min_chars} characters")
        assert(value.length <= params.max_chars,
               "{value.name} must be at most {params.max_chars} characters")
    }
}
```

- **Properties** — `name: Type [= default]`, the same shape as a struct field
  (no `;`, no `optional`, no annotations). The validator's configuration, filled
  in at the use site.
- **`validate { … }`** — one or more `assert(condition, message)` calls.
  - `condition` — a small expression: member paths over `value.*` (the field
    being checked) and `params.*` (this validator's properties), comparisons
    (`== != >= <= > <`), and `and` / `or` chains. **No precedence** — it is
    captured as text, [not evaluated](#constraint-stays-non-turing-complete).
  - `message` — the [interpolated string](../guide/idl/error.md#message) rule,
    reused; `{value.…}` / `{params.…}` placeholders work.
  - **`assert(c, m)` holds when `c` is true**; a false `c` fails validation with
    `m`.
- Frozen as `FrozenUnit::Validator { properties, expression_block }`, where the
  block is `ExpressionBlock { function_calls: Vec<String> }` — each assert
  reconstructed to canonical text.

### The `@validators` field annotation

```
struct Message {
    @validators = [StringBounds(min_chars = 3, max_chars = 12)]
    recipient: str
}
```

- A **list** of **calls**: `ValidatorName(prop = value, …)`, comma-separated
  keyword args. Empty args (`A()`) and empty lists (`[]`) parse.
- Captured onto the field as a `FrozenUnit::Property` whose value is the
  normalised text `[StringBounds(min_chars = 3, max_chars = 12)]`. It is **not**
  yet resolved against the declared validator.
- Works on `struct` and `error` fields (same `Field` grammar).

## Where validation runs

Two distinct jobs, neither done yet:

1. **Well-formedness (compile time).** `@validators` names a real validator and
   binds real properties with type-correct values; a `validate` block references
   only declared `params`. `validator.rs`-style work in `core`; gates
   `comline build`. This is **phase 3** and needs the captured text parsed into
   structure rather than left as strings.
2. **The actual check (run time).** `StringBounds(min_chars = 3)` on a field runs
   when a message is decoded — emitted into generated code / enforced by the
   [runtime](../guide/runtime/index.md), the layer that does serialization.
   **Phase 4.**

## Phasing

| Phase | State |
|---|---|
| 1 — `validator` declaration + typed properties | ✅ core#32 |
| 1b — `validate { assert(…) }` block, captured as text | ✅ core#33 |
| 2 — `@validators = [Name(a = 1)]` list/call annotation values | ✅ core#34 |
| 3 — compile-time resolution: parse the captured text; resolve names / kwargs / `params` refs; gate `build` | — |
| 4 — runtime enforcement: generators emit the checks; define the failure surface | — |

## Constraint: stays non-Turing-complete

`validate` is a checking language, not a scripting one. Whatever it grows —
`let`, helpers, regex — it must stay **total**: no recursion, no unbounded
iteration. A field check that might not terminate is a bug, not a feature. This
bounds the answers to the questions below.

## Open questions

- **`validate` as text vs. AST.** `ExpressionBlock { function_calls: Vec<String> }`
  is text capture. Phase 3 (compile-time checks) and phase 4 (codegen) need it
  parsed into structure — decide the AST shape then.
- **`assert` vocabulary.** Only `assert(cond, msg)` exists. Does `validate` stay
  that minimal, or grow `let` / early `return` / regex helpers (within the
  non-TC constraint)?
- **Scoped-const property defaults.** `min_chars: u32 = 0` today; `= u32::MIN` /
  `= SOME_CONST` would need scoped paths in default position (a general grammar
  gap, not validator-specific).
- **Failure surface.** What does a failed validator produce at run time — an
  `error`, a panic, a `Result`? Can a schema pick "collect all failures" vs.
  "fail fast"?

## Resolved along the way

- **Property terminators** — no `;`; matches struct fields (core#32).
- **Kwarg separator** — commas: `min_chars = 3, max_chars = 12` (core#34).
- **`string_bounds.ids`** — the inverted `assert` in the stdlib example was
  corrected when the block landed (core#33).
