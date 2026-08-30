# Constants

A **constant** is a named, compile-time value.

```
const WORLD_COUNT: u8 = 10
const DEFAULT_NAME: str = "flower"
```

```
const NAME: Type = value
```

- **`NAME`** — a plain identifier (not scoped).
- **`Type`** — any [type](structure.md#field-types); in practice a primitive.
- **`value`** — a literal: an integer, a `"quoted string"`, or an identifier.
  String literals are plain — no interpolation (that exists only in an
  [`error`](error.md)'s `message`).

A constant can carry a [docstring](docstrings.md):

```
/// Largest number of worlds a provider may report.
const WORLD_COUNT: u8 = 10
```

## Using one

A constant is referenced by name as a struct [field default](structure.md#fields):

```
struct Person {
    name: str = DEFAULT_NAME
}
```

Array sizes currently take an integer literal only (`Article[10]`), not a
constant name.
