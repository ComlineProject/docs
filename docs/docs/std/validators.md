# `validators`

Validators to attach to fields with `@validators`.

Each takes its parameters by name:

    @validators = [MinChars(min = 3)]

A maximum belongs in the type (`char[max 32]`, `u32[max 10]`), where a
decoder checks it before allocating. These check what a type can't say:
a minimum, or a range of values.

| Item | Summary |
|---|---|
| validator [`NonEmpty`](#nonempty) | Checks a string or a list isn't empty. |
| validator [`MinChars`](#minchars) | Checks a string has at least `min` characters. |
| validator [`MinItems`](#minitems) | Checks a list has at least `min` items. |
| validator [`IntRange`](#intrange) | Checks an integer is within `min` and `max`, both included. |
| validator [`StringBounds`](#stringbounds) | Checks a string's length is within a minimum and a maximum. |

<a id="nonempty"></a>

## validator `NonEmpty`

Checks a string or a list isn't empty.

Applies to: `string`, `any``[]`

| Assert | Message |
|---|---|
| `value.length > 0` | {value.name} must not be empty |

<a id="minchars"></a>

## validator `MinChars`

Checks a string has at least `min` characters.

Applies to: `string`

| Parameter | Type | Description |
|---|---|---|
| `min` | `u32` | the fewest characters allowed |

| Assert | Message |
|---|---|
| `value.length >= params.min` | {value.name} must be at least {params.min} characters |

<a id="minitems"></a>

## validator `MinItems`

Checks a list has at least `min` items.

Applies to: `any``[]`

| Parameter | Type | Description |
|---|---|---|
| `min` | `u32` | the fewest items allowed |

| Assert | Message |
|---|---|
| `value.length >= params.min` | {value.name} must have at least {params.min} items |

<a id="intrange"></a>

## validator `IntRange`

Checks an integer is within `min` and `max`, both included.

Applies to: `u8`, `u16`, `u32`, `u64`, `s8`, `s16`, `s32`, `s64`

| Parameter | Type | Description |
|---|---|---|
| `min` | `s64` = `s64::MIN` | the smallest value allowed |
| `max` | `u64` = `u64::MAX` | the largest value allowed |

| Assert | Message |
|---|---|
| `value >= params.min` | {value.name} must be at least {params.min} |
| `value <= params.max` | {value.name} must be at most {params.max} |

<a id="stringbounds"></a>

## validator `StringBounds`

Checks a string's length is within a minimum and a maximum.

Deprecated in spirit: the type carries the maximum (`char[max 32]`), and
`MinChars` the minimum. `max_chars` defaults to no limit, so it never
refuses what the type allows.

Applies to: `string`

| Parameter | Type | Description |
|---|---|---|
| `min_chars` | `u32` = `0` | minimum length of the string |
| `max_chars` | `u32` = `u32::MAX` | maximum length of the string |

| Assert | Message |
|---|---|
| `value.length >= params.min_chars` | {value.name} must be at least {params.min_chars} characters |
| `value.length <= params.max_chars` | {value.name} must be at most {params.max_chars} characters |
