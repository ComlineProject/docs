# Validators

!!! note "Checked, not run"
    `comline build` verifies validators — an unknown validator name, a validator
    put on a field of a type it doesn't apply to, a keyword argument that isn't a
    property or whose literal type is wrong, or an undeclared `params.*`
    reference all fail the build. Running them against data
    (in generated code) is not done yet — see the
    [design note](../../design/validators.md).

A **validator** is a named, parameterised check you attach to a
[struct](structure.md) or [error](error.md) field.

```ids linenums="1"
/// Checks a string's length is within bounds.
/// @min_chars: minimum length
/// @max_chars: maximum length
validator StringBounds for string {
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

## Target types — `for`

Every validator names the type(s) it checks, after `for`. A validator without
`for` is a build error.

```ids
validator StringBounds for string { … }
validator Range for u8, u16, u32 { … }
```

- A field can take a validator only if its type is one of the targets, matched
  exactly: a `u8` field doesn't take a `for u32` validator.
- A [`type` alias](types.md) counts as the type it stands for, so a field of
  type `type Name = string` takes a `for string` validator.
- An `optional` field is checked as its inner type.
- On an array field, a validator checks the **array**, not each element: a
  `for string` validator doesn't go on a `string[]` field.
- Targets are primitives, arrays of them, or aliases. There are no generic
  targets; list each type instead.

## Properties

`name: Type [= default]`, one per line — the same shape as a
[struct field](structure.md#fields), minus `optional` and annotations. They are
the validator's configuration, supplied where the validator is used.

## `validate`

A `validate` block holds one or more `assert(condition, message)` calls.

- **`condition`** — member paths over `value.*` (the field under check) and
  `params.*` (this validator's properties), compared with `== != >= <= > <` and
  joined by `and` / `or`. `assert(c, m)` passes when `c` is true. Numbers
  compare by value, so a `u8` value against a `u32` property is fine.
- **`value` accessors** — `value` itself, `value.length` (only when every
  target is `string` or an array), and `value.name` (the field's name, for
  messages). Anything else is a build error at the validator.
- **`message`** — an [interpolated string](error.md#message); `{value.…}` and
  `{params.…}` placeholders are substituted.

The condition language is deliberately small and
[non-computational](../../design/validators.md#constraint-stays-non-turing-complete)
— no precedence, no loops, no bindings.

## Using one — `@validators`

Attach validators to a field with the `@validators` annotation: a list of calls
that bind the validator's properties by name.

```ids linenums="1"
struct Message {
    @validators = [StringBounds(min_chars = 3, max_chars = 12)]
    recipient: string
}
```

Unbound properties fall back to their declared default. Errors' fields take
`@validators` too. Validators imported with `use` (such as
`std::validators::StringBounds`) are checked the same way as local ones.
