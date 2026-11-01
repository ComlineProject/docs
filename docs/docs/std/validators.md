# `validators`

Validators to attach to fields with `@validators`.

Each takes its parameters by name:

    @validators = [StringBounds(min_chars = 3, max_chars = 32)]

| | |
|---|---|
| validator [`StringBounds`](#stringbounds) | Checks a string's length is within a minimum and a maximum. |

<a id="stringbounds"></a>

## validator `StringBounds`

Checks a string's length is within a minimum and a maximum.

Applies to: `string`

| Parameter | Type | |
|---|---|---|
| `min_chars` | `u32` = `0` | minimum length of the string |
| `max_chars` | `u32` = `1024` | maximum length of the string |

| Assert | Message |
|---|---|
| `value.length >= params.min_chars` | {value.name} must be at least {params.min_chars} characters |
| `value.length <= params.max_chars` | {value.name} must be at most {params.max_chars} characters |
