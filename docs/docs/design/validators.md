# Validators

Status: **not implemented** · design only · builds on annotation capture (core#31)

A **validator** is a named, parameterised check attached to a
[struct](../guide/idl/structure.md) or [error](../guide/idl/error.md) field. Two
`.ids` files already assume it (`core_stdlib/.../validators/string_bounds.ids`,
`core/tests/schema/simple.ids`), but nothing parses or runs it yet.

## Intended shape

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

- **Properties** — `name: Type [= default]`, the same shape as a struct field.
  They are the validator's configuration, filled in at the use site.
- **`validate { … }`** — one or more `assert(condition, message)` calls.
  - `condition` is a boolean expression over `value.*` (the field being checked
    — `value.length`, `value.name`, …) and `params.*` (this validator's
    properties). Operators: comparisons, `and` / `or`, `not`.
  - `message` is an [interpolated string](../guide/idl/error.md#message) with
    `{value.…}` / `{params.…}` placeholders.
  - **`assert(c, m)` holds when `c` is true**; a false `c` fails validation with
    `m`. The current `string_bounds.ids` has this inverted (it asserts the
    *failure* condition, with a success-worded message) — the example needs
    fixing along with the implementation.

### The `@validators` field annotation

```
struct Message {
    @validators = [StringBounds(min_chars = 3, max_chars = 12)]
    recipient: str
}
```

- Value is a **list** of **calls**: `ValidatorName(prop = value, …)`.
- Each call binds the validator's properties by name; unbound properties take
  their declared default.
- Works on `struct` and `error` fields (both use the same `Field` grammar).

## What has to change

| Piece | Today | Needed |
|---|---|---|
| `validator` declaration | no grammar rule | `Declaration::Validator` + rule; `FrozenUnit::Validator` already exists |
| `validate {}` block | — | v1: capture each `assert(…)` as text into `FrozenUnit::ExpressionBlock { function_calls: Vec<String> }` (already defined). A real parsed expression AST is a later step. |
| Property defaults like `u32::MIN` | `const`/default values are `int \| string \| ident` only | either allow scoped-const paths in default position, or restrict validator defaults to plain literals |
| `@validators = [ … ]` | annotation value is a single `Expression` | extend annotation values to a **list literal** and a **call with named args**. Depends on core#31 (annotations are now captured; today only scalar values). |
| Interpolation roots | `error`'s `message` interpolates `self.*` | add `value.*` / `params.*` roots for `validate` messages |

## Where validation runs

Two distinct jobs:

1. **Well-formedness (compile time).** The `validator` declaration parses, its
   `validate` block references only declared `params`, `@validators=[…]` names a
   real validator and binds real properties with type-correct values. This is
   `validator.rs`-style work in `core` and gates `comline build`.
2. **The actual check (run time).** `StringBounds(min_chars=3)` on a `recipient`
   field runs when a message is decoded. That is **not** a compile-time check —
   it is emitted into generated code / enforced by the [runtime](../guide/runtime/index.md),
   the same layer that does serialization. v1 can stop at job 1 and record the
   validators in the IR without emitting runtime checks yet.

## Phasing

1. **`validator` declaration** — grammar + `Declaration::Validator` → `FrozenUnit::Validator`, `validate {}` captured as call-text. Well-formedness of the block deferred.
2. **Annotation value grammar** — list literals + calls with named args, so `@validators = [Name(a = 1)]` parses; capture into the field's `parameters` (extends core#31).
3. **Compile-time checks** — `@validators` names/props resolve against the declared `validator`; `validate` block references only known `params`.
4. **Runtime enforcement** — code generators emit the checks; define the failure surface (an `error`? a panic? a `Result`?).

## Open questions

- **`validate` as text vs. AST.** `ExpressionBlock { function_calls: Vec<String> }` implies text capture. Fine for v1, but compile-time checks (phase 3) and codegen (phase 4) need structure. Decide when to parse the expression language properly.
- **Property terminators.** `string_bounds.ids` ends property lines with `;`; struct fields do not. Pick one.
- **`assert` vs. multiple styles.** Only `assert(cond, msg)` is shown. Is that the whole vocabulary, or will `validate` grow `let`, early `return`, regex helpers, etc.?
- **Kwarg separator.** `simple.ids` writes `min_chars=3 max_chars=12` (space-separated). Commas (`min_chars = 3, max_chars = 12`) read better and match the rest of the language — this doc assumes commas.
- **Failure surface.** What does a failed validator produce at run time, and can a schema opt into "collect all failures" vs. "fail fast"?
