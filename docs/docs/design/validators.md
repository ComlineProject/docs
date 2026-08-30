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
  `Result<(), Vec<ValidationError>>` — **collect all** failures. Codegen also
  emits `validate_first(&self) -> Result<(), ValidationError>` for callers that
  want to stop at the first. Deserialization calls neither automatically unless
  [`comline.toml` opts in](#auto-validation-on-decode-4c).
- **`ValidationError`** is a small shared type from a runtime support crate
  (`comline_rt` — the dormant `runtime` repo's first real job):
  `{ field: &'static str, message: String }`; `ValidationErrors(Vec<_>)` wraps
  it for the auto-run path. It is **not** one of the schema's `error`
  declarations — validators aren't linked to an `error` today.
- **`params.*` are inlined at codegen.** `min_chars = 3` bakes the literal `3`
  into the check; an unbound property emits its declared default. No runtime
  parameter passing, no per-instance validator object.
- **`value.*` accessor vocabulary** — small, fixed, and **type-checked at the
  use site**:

  | path | defined for | lowers to (rust) |
  |---|---|---|
  | `value` | any field | `&self.<field>` |
  | `value.length` | `str`, arrays (`T[]`) | `.chars().count()` / `.len()` |
  | `value.name` | any field (compile-time string) | `"<field>"` |

  `value` is whatever field the validator is attached to — its type is known
  only where `@validators` names the validator, not in the `validator`
  declaration. So each `value.<accessor>` is checked **per application**: when
  `StringBounds(…)` is put on `recipient: str`, `value.length` resolves;
  putting the same validator on an `s32` field is a `comline build` error at
  that field. An unsupported or unknown accessor never reaches codegen — the
  generator only ever sees accessor/type pairs that already type-checked. The
  set grows deliberately and stays
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
| 4b | `rust` generator emits `validate()` (collect-all) and `validate_first()` (fail-fast); stand up the `comline_rt` support crate with `ValidationError` / `ValidationErrors`; implement the `value.*` accessor set. |
| 4c | `comline.toml` `validate_on_decode` knob (`off` / `collect` / `first`) — `#[serde(try_from)]` shim in the `rust` target; default `off`. [Sketch below](#auto-validation-on-decode-4c). |
| 4d | The other generators (python / typescript / luau) once they exist; imported / cross-schema validators (needs the imported schema's IR at generate time, like multi-version `generate`). |

### Auto-validation on decode (4c)

Whether decode runs the checks is the **consumer's** call, not the schema's — it
changes the shape and cost of generated decode (a clone per decode, no "parse
now, validate later"), which is a codegen concern. So it's a `[generate]` key in
the consumer's [`comline.toml`](../reference/comline-toml.md), overridable per
`[[generate.target]]`, slotting into the existing
`defaults → [generate] → [[generate.target]] → env → CLI` precedence:

```toml
[generate]
# Run the validators as part of decoding. Off by default.
#   "off"     — emit validate() / validate_first(), never call them for you
#   "collect" — decode, then collect-all; Err is ValidationErrors(Vec<_>)
#   "first"   — decode, then fail-fast; Err is ValidationError
validate_on_decode = "off"

[[generate.target]]
language           = "rust"
validate_on_decode = "collect"
```

- **rust** — `"collect"` / `"first"` add `#[serde(try_from = "…")]` (a shadow
  type that decodes the raw shape, then calls `validate()` / `validate_first()`
  in its `TryFrom`); `"off"` leaves decode untouched.
- Matching `COMLINE_GENERATE_VALIDATE_ON_DECODE` env var and
  `--validate-on-decode` flag, like the other `[generate]` keys.
- Folds into [`comline.toml`](../reference/comline-toml.md) when 4c ships.

### Decided

- **Trigger point.** `validate()` is always emitted (4b) and the caller invokes
  it. Auto-running it on decode is opt-in via
  [`comline.toml`](#auto-validation-on-decode-4c), not the IDL — it's a codegen
  concern, not a schema contract. Default: off.
- **Fail-fast vs collect-all.** Not a schema property and not a package
  `settings` — it's how the *consumer* wants failures surfaced, and a form UI
  and a hot-path decoder want opposite things from the same type. So codegen
  emits both verbs (`validate()` collect-all, `validate_first()` fail-fast) and
  the caller picks; the auto-run path picks with `validate_on_decode`. A
  package-level toggle would fragment `.validate()`'s meaning across
  dependencies, so there isn't one. Either way codegen must emit **panic-safe**
  checks — an assert that indexes past what an earlier assert guards has to
  evaluate to *failure*, not crash.
- **Unsupported `value` accessor.** A `comline build` error at the field that
  applies the validator (see the [accessor table](#proposed-generated-shape-rust)).
  `length` is an attribute of the types that have one; on a type that doesn't,
  the schema never compiles — it never reaches codegen, let alone runtime.
  There is no "emit vs. don't emit" fork.

### Open questions

- **Runtime `params`.** The design inlines every arg at codegen (literal or
  `const`). Whether a dynamic arg is ever wanted — and what it would do to the
  inline model — is undecided; no position yet.
- **`assert` vocabulary.** Only `assert(cond, msg)` today. Whether it grows
  (a `regex` / `matches` helper, `let` bindings, …) is undecided. Whatever the
  answer, it stays bounded by the
  [non-TC constraint](#constraint-stays-non-turing-complete).

## Resolved along the way

- **Property terminators** — no `;`; matches struct fields (core#32).
- **Kwarg separator** — commas: `min_chars = 3, max_chars = 12` (core#34).
- **`string_bounds.ids`** — the inverted `assert` in the stdlib example was
  corrected when the block landed (core#33).
- **Scoped-const property defaults** — `= u32::MIN` / `= SOME_CONST` now parse
  (`Expression::Path` / `Expression::FString`, core#36).
- **`validate` as text vs. AST** (for the checks) — resolved by the structured
  `Assert` in core#39. A full operator AST is [phase 4a](#prerequisite-a-real-condition-ast-in-the-ir-4a).
