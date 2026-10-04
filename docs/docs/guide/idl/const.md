# Constants

A **constant** is a named, compile-time value.

```ids
const WORLD_COUNT: u8 = 10
const DEFAULT_NAME: str = "flower"
```

```ids
const NAME: Type = value
```

- **`NAME`** — a plain identifier (not scoped).
- **`Type`** — any [type](structure.md#field-types); in practice a primitive.
- **`value`** — one of:
    - a literal: an integer or a `"quoted string"` (plain, no interpolation)
    - an identifier — another constant, by name
    - a `::`-path — `u32::MIN`, `pkg::mod::DEFAULT`
    - an **f-string** — `f"page {N} of {total}"`, with `{path}` placeholders and
      `{{` / `}}` escapes (same interpolation as an [`error`](error.md)'s
      `message`)

Everything except a plain literal is recorded as text and **not resolved to a
value yet** — including the `{N}` in an f-string.

A constant can carry a [docstring](docstrings.md):

```ids
/// Largest number of worlds a provider may report.
const WORLD_COUNT: u8 = 10
```

## Using one

A constant is referenced by name as a struct [field default](structure.md#fields):

```ids
struct Person {
    name: str = DEFAULT_NAME
}
```

Array sizes currently take an integer literal only (`Article[10]`), not a
constant name.
