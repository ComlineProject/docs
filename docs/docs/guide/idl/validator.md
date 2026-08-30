# Validators

!!! note "Recorded, not enforced"
    Validators parse and are frozen into the version, but nothing checks against
    them yet — see the [design note](../../design/validators.md) for the
    remaining phases.

A **validator** is a named, parameterised check you attach to a
[struct](structure.md) or [error](error.md) field.

``` py linenums="1"
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

## Properties

`name: Type [= default]`, one per line — the same shape as a
[struct field](structure.md#fields), minus `optional` and annotations. They are
the validator's configuration, supplied where the validator is used.

## `validate`

A `validate` block holds one or more `assert(condition, message)` calls.

- **`condition`** — member paths over `value.*` (the field under check) and
  `params.*` (this validator's properties), compared with `== != >= <= > <` and
  joined by `and` / `or`. `assert(c, m)` passes when `c` is true.
- **`message`** — an [interpolated string](error.md#message); `{value.…}` and
  `{params.…}` placeholders are substituted.

The condition language is deliberately small and
[non-computational](../../design/validators.md#constraint-stays-non-turing-complete)
— no precedence, no loops, no bindings.

## Using one — `@validators`

Attach validators to a field with the `@validators` annotation: a list of calls
that bind the validator's properties by name.

``` py linenums="1"
struct Message {
    @validators = [StringBounds(min_chars = 3, max_chars = 12)]
    recipient: str
}
```

Unbound properties fall back to their declared default. Errors' fields take
`@validators` too.
