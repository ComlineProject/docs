# Validators

Status: **compile-time checks done** (core#32–40) · **not run** — codegen /
runtime enforcement is phase 4 (design below)

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
  `validator`, that each keyword arg is one of its properties, and that a
  **literal** arg's type category (string / integer / bool) matches the property
  type (core#40). Arg values that are `const` references are not type-checked —
  they stay text in the IR.
- Works on `struct` and `error` fields (same `Field` grammar).

## Where validation runs

1. **Well-formedness (compile time).** Done (core#37–40): `@validators` names a
   real validator, keyword args are real properties with matching literal types,
   `validate` blocks reference only `value.*` / declared `params.*`. Gated on
   `comline build`.
2. **The actual check (run time).** `StringBounds(min_chars = 3)` on a field runs
   when a message is decoded — emitted into generated code / enforced by the
   [runtime](../guide/runtime/index.md), the layer that does serialization.
   **Phase 4**, drafted below, not started.

## Phasing

| Phase | State |
|---|---|
| 1 — `validator` declaration + typed properties | ✅ core#32 |
| 1b — `validate { assert(…) }` block | ✅ core#33 |
| 2 — `@validators = [Name(a = 1)]` list/call annotation values | ✅ core#34 |
| 3a — resolve `@validators` names | ✅ core#37 |
| 3b — check `@validators` keyword-arg names | ✅ core#38 |
| 3c — structured `validate` block, check `params.*` refs | ✅ core#39 |
| 3d — check keyword-arg literal **types** against the property types | ✅ core#40 |
| 4 — runtime enforcement: generators emit the checks | drafted ([below](#phase-4-runtime-enforcement-design)) — not started |

## Constraint: stays non-Turing-complete

`validate` is a checking language, not a scripting one. Whatever it grows —
`let`, helpers, regex — it must stay **total**: no recursion, no unbounded
iteration. A field check that might not terminate is a bug, not a feature. This
bounds the answers to the questions below.

## Phase 4 — runtime enforcement (design)

### Where codegen is today

`comline generate` (the `rust` target,
`core/core/src/codelib_gen/rust.rs`) emits plain data: `#[derive(Serialize,
Deserialize)] pub struct`s, `pub trait`s for protocols, C-like `enum`s. No
`validate`, no decode hook, no runtime crate — the `runtime` repo is dormant.
`@validators` is frozen onto the field IR and then ignored by every generator.
Phase 4 is greenfield: nothing to retrofit, only something to add.

### What "run" means

`StringBounds(min_chars = 3, max_chars = 12)` on `Message.recipient` should turn
into an actual bounds check on the string, run when a `Message` crosses a trust
boundary (decoded from the wire, built by a client). The generated code carries
the check; nothing outside the generated code has to know the validator existed.

### Proposed generated shape (rust)

```rust
impl Message {
    /// Every `@validators` check on this value. Collects all failures.
    pub fn validate(&self) -> Result<(), Vec<::comline_rt::ValidationError>> {
        let mut failures = Vec::new();

        // recipient: StringBounds(min_chars = 3, max_chars = 12)
        {
            let value = &self.recipient;
            let value_name = "recipient";
            // assert(value.length >= params.min_chars, ...)
            if !((value.chars().count() as u64) >= 3u64) {
                failures.push(::comline_rt::ValidationError {
                    field: value_name,
                    message: format!("{value_name} must be at least {} characters", 3u64),
                });
            }
            // assert(value.length <= params.max_chars, ...)
            if !((value.chars().count() as u64) <= 12u64) {
                failures.push(::comline_rt::ValidationError {
                    field: value_name,
                    message: format!("{value_name} must be at most {} characters", 12u64),
                });
            }
        }

        if failures.is_empty() { Ok(()) } else { Err(failures) }
    }
}
```

Decisions baked into that shape:

- **An explicit `validate(&self)` method**, returning
  `Result<(), Vec<ValidationError>>` — **collect all** failures, not fail-fast.
  Deserialization does *not* call it automatically (see 4c); a caller runs it at
  the boundary it cares about.
- **`ValidationError`** is a small shared type from a runtime support crate
  (`comline_rt` — the dormant `runtime` repo's first real job):
  `{ field: &'static str, message: String }`. It is **not** one of the schema's
  `error` declarations — validators aren't linked to an `error` today.
- **`params.*` are inlined at codegen.** `min_chars = 3` bakes the literal `3`
  into the check; an unbound property emits its declared default. No runtime
  parameter passing, no per-instance validator object.
- **`value.*` accessor vocabulary** — small and fixed:

  | path | meaning | lowers to (rust) |
  |---|---|---|
  | `value` | the field's value | `&self.<field>` |
  | `value.length` | char / element count | `.chars().count()` (str), `.len()` (array) |
  | `value.name` | the field name, for messages | `"<field>"` |

  Anything else is a build error. The set grows deliberately and stays
  [non-computational](#constraint-stays-non-turing-complete).
- **Operators** map straight through: `== != >= <= > <` → the rust operators,
  `and` / `or` → `&& ||`, each comparison parenthesised (the grammar has no
  precedence, so codegen supplies the grouping).
- **Message interpolation** — the `{value.name}` / `{params.x}` placeholders
  become `format!` arguments with the inlined values.

### Prerequisite: a real condition AST in the IR (4a)

The frozen `Assert` keeps `condition` as **canonical text** plus a flat
`references: Vec<String>`. That was enough for the compile-time checks (does
every `params.x` name a property?), but a code generator needs the operator
tree. Phase 4 starts by freezing the condition structurally, e.g.:

```rust
Assert {
    condition: Box<FrozenUnit>,   // was: String
    message: String,
    references: Vec<String>,       // kept — the checks still use it
}

// new operand / expression units
BoolExpr   { op: String /* "and" | "or" */, terms: Vec<FrozenUnit> },
Comparison { op: String /* "==" .. "<" */, left: Box<FrozenUnit>, right: Box<FrozenUnit> },
Operand    { ... }   // path "value.length" | integer | string
```

`grammar.rs` already parses this shape (`Condition` / `ConditionTail` /
`Comparison` / `Operand`); 4a is a freezing change in `incremental.rs` plus the
`generation.rs` tests — no grammar work. Keep the `condition` text available
(derive it from the tree) so the `validator.rs` messages don't regress.

### Phasing

| Sub-phase | Work |
|---|---|
| 4a | Freeze the `validate` condition as a structured expression tree (keep the text + `references` the checks use). |
| 4b | `rust` generator emits `fn validate(&self) -> Result<(), Vec<ValidationError>>`; stand up the `comline_rt` support crate with `ValidationError`; implement the `value.*` accessor set. |
| 4c | Opt-in auto-validation on decode — `#[serde(try_from = "…")]` shim, or a documented "call `.validate()` after decode" contract. |
| 4d | The other generators (python / typescript / luau) once they exist; imported / cross-schema validators (needs the imported schema's IR at generate time, like multi-version `generate`). |

### Open questions

- **Trigger point (4c).** Explicit `.validate()` call, or always-run on
  deserialize via `#[serde(try_from)]`? Auto-run is safer by default but costs a
  clone on every decode and removes the "parse now, validate later" option.
  Leaning: emit the method in 4b, make auto-run an opt-in `settings` toggle
  in 4c.
- **`value.length` on a type with no length.** A length check on an `s32` field
  — reject at `comline build` (4a / `validator.rs`), or just don't emit? Reject:
  it is always a mistake.
- **Fail-fast vs collect-all.** The shape above is collect-all (`Vec<_>`). A
  `settings` knob could pick fail-fast. Not worth it until asked for.
- **Runtime `params`.** Still assuming every arg is compile-time-known (literal
  or `const`). A future dynamic arg would break the "inline at codegen" model.
  No use case yet.
- **`assert` vocabulary.** Only `assert(cond, msg)`. A `regex` / `matches`
  helper is the likely first extension — must stay total (a bounded matcher, no
  catastrophic backtracking).

## Resolved along the way

- **Property terminators** — no `;`; matches struct fields (core#32).
- **Kwarg separator** — commas: `min_chars = 3, max_chars = 12` (core#34).
- **`string_bounds.ids`** — the inverted `assert` in the stdlib example was
  corrected when the block landed (core#33).
- **Scoped-const property defaults** — `= u32::MIN` / `= SOME_CONST` now parse
  (`Expression::Path` / `Expression::FString`, core#36).
- **`validate` as text vs. AST** (for the checks) — resolved by the structured
  `Assert` in core#39. A full operator AST is [phase 4a](#prerequisite-a-real-condition-ast-in-the-ir-4a).
