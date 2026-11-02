# Constants

A **constant** is a named, compile-time value.

```ids
const WORLD_COUNT: u8 = 10
const DEFAULT_NAME: string = "flower"
```

```ids
const NAME: Type = value
```

- **`NAME`** — a plain identifier (not scoped).
- **`Type`** — any [type](structure.md#field-types); in practice a primitive.
- **`value`** — one of:
    - a literal: an integer, `true` / `false`, or a `"quoted string"` (plain,
      no interpolation)
    - another constant, by name — `WORLD_COUNT`, or `pkg::mod::DEFAULT` for one
      another schema declares
    - an integer type's bound — `u32::MIN`, `u64::MAX`

A value that names a constant or a bound is checked as the value it comes to.
It has to be the constant's kind of value (an integer is also a fine float)
and, for an integer, fit the declared width:

```ids
const LIMIT: u32 = 500
const SMALL: u8 = LIMIT     // error: `LIMIT` is 500, which does not fit in `u8`
const TOP: u64 = u64::MAX   // fine
```

A name that isn't a constant is an error, and so are constants that name each
other in a loop. Generated code holds the value a name comes to, as if the
literal had been written.

A constant can carry a [docstring](docstrings.md):

```ids
/// Largest number of worlds a provider may report.
const WORLD_COUNT: u8 = 10
```

## Using one

A constant is referenced by name wherever a value is written: a struct's or an
error's [field default](structure.md#fields), a validator property's default,
or a validator's argument. It's checked there the same way, against the type
it's written for:

```ids
struct Person {
    name: string = DEFAULT_NAME
    worlds: u8 = WORLD_COUNT
}
```

Array sizes currently take an integer literal only (`Article[10]`), not a
constant name.
