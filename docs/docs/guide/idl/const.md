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

## Sizes from constants

An array's size can be a constant, in a maximum or an exact length:

```ids
const NAME_MAX: u8 = 32
const LIMIT: u32 = 500

struct Customer {
    name: char[max NAME_MAX]
    code: char[NAME_MAX]
    orders: Order[max LIMIT]
    chunk: u8[max u16::MAX]
}
```

- **It names an unsigned integer constant:** declared `u8`, `u16`, `u32` or
  `u64`, in this schema or another (`pkg::mod::NAME_MAX`), or an unsigned type's bound such as `u16::MAX`. A signed
  or non-integer constant, or a name that isn't a constant, is a build error
  saying so.
- **It is stored resolved.** The stored schema holds the number, so the
  maximum is the same wherever the constant came from, and changing the
  constant changes the type, which is a breaking change like any other bound
  change.
- **The same limits apply:** at least 1 and at most `u32::MAX`, so a constant of
  `0` is an error where it is used as a size.

See [Bounds](types.md#bounds) for what a maximum means.
