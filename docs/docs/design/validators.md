# Validators

Status: **compile-time checks land** (core#32–39) · **not run** — codegen /
runtime enforcement is phase 4

A **validator** is a named, parameterised check attached to a
[struct](../guide/idl/structure.md) or [error](../guide/idl/error.md) field. The
declaration, its `validate` block, and the `@validators` field annotation parse,
freeze into structured IR, and are checked at `comline build` time — unknown
validator, bad keyword arg, undeclared `params.*` reference all fail the build.
Nothing *runs* them against data yet.

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
    [not evaluated](#constraint-stays-non-turing-complete), only checked.
  - `message` — the [interpolated string](../guide/idl/error.md#message) rule,
    reused; `{value.…}` / `{params.…}` placeholders work.
  - **`assert(c, m)` holds when `c` is true**; a false `c` fails validation with
    `m`.
- Frozen as `FrozenUnit::Validator { properties, expression_block }`, where the
  block is `ExpressionBlock { asserts: [Assert { condition, message, references }] }`.
  Each `params.*` / `value.*` in a `condition` is checked against the validator's
  properties; unknown roots and unknown `params.*` fail the build.

### The `@validators` field annotation

```
struct Message {
    @validators = [StringBounds(min_chars = 3, max_chars = 12)]
    recipient: str
}
```

- A **list** of **calls**: `ValidatorName(prop = value, …)`, comma-separated
  keyword args. Empty args (`A()`) and empty lists (`[]`) parse.
- Frozen onto the field as one `FrozenUnit::ValidatorRef { name, args }` per
  call. `validator.rs` checks the name resolves to a declared (or imported)
  `validator`, and that each keyword arg is one of its properties. Argument
  **value types** are not checked yet — arg values are still text in the IR.
- Works on `struct` and `error` fields (same `Field` grammar).

## Where validation runs

1. **Well-formedness (compile time).** Mostly done (core#37–39): `@validators`
   names a real validator, keyword args are real properties, `validate` blocks
   reference only `value.*` / declared `params.*`. Gated on `comline build`.
   Remaining: keyword-arg **value types**.
2. **The actual check (run time).** `StringBounds(min_chars = 3)` on a field runs
   when a message is decoded — emitted into generated code / enforced by the
   [runtime](../guide/runtime/index.md), the layer that does serialization.
   **Phase 4**, not started.

## Phasing

| Phase | State |
|---|---|
| 1 — `validator` declaration + typed properties | ✅ core#32 |
| 1b — `validate { assert(…) }` block | ✅ core#33 |
| 2 — `@validators = [Name(a = 1)]` list/call annotation values | ✅ core#34 |
| 3a — resolve `@validators` names | ✅ core#37 |
| 3b — check `@validators` keyword-arg names | ✅ core#38 |
| 3c — structured `validate` block, check `params.*` refs | ✅ core#39 |
| 3d — check keyword-arg value **types** against the property types | — (arg values still text in the IR) |
| 4 — runtime enforcement: generators emit the checks; failure surface | — |

## Constraint: stays non-Turing-complete

`validate` is a checking language, not a scripting one. Whatever it grows —
`let`, helpers, regex — it must stay **total**: no recursion, no unbounded
iteration. A field check that might not terminate is a bug, not a feature. This
bounds the answers to the questions below.

## Open questions

- **A real condition AST.** The frozen `Assert` keeps `condition` as canonical
  text plus a flat `references` list — enough for the compile-time checks, not
  for phase 4 (codegen needs the operator tree). Decide the AST shape when
  starting phase 4.
- **`assert` vocabulary.** Only `assert(cond, msg)` exists. Does `validate` stay
  that minimal, or grow `let` / early `return` / regex helpers (within the
  non-TC constraint)?
- **Failure surface.** What does a failed validator produce at run time — an
  `error`, a panic, a `Result`? Can a schema pick "collect all failures" vs.
  "fail fast"?

## Resolved along the way

- **Property terminators** — no `;`; matches struct fields (core#32).
- **Kwarg separator** — commas: `min_chars = 3, max_chars = 12` (core#34).
- **`string_bounds.ids`** — the inverted `assert` in the stdlib example was
  corrected when the block landed (core#33).
- **Scoped-const property defaults** — `= u32::MIN` / `= SOME_CONST` now parse
  (`Expression::Path` / `Expression::FString`, core#36).
- **`validate` as text vs. AST** (for the checks) — resolved by the structured
  `Assert` in core#39. A full operator AST is still deferred to phase 4.
