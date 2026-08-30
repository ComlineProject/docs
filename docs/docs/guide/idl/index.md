# IDL / Schema

The **Interface Description Language** (IDL, also called the *schema*) is what you
write by hand. A schema file has the extension `.ids` and lives under a project's
`src/` directory. It defines the data shapes and the protocols that carry them,
independent of any language.

```
// greeting.ids
const GREETING_MAX: u16 = 280

enum Language {
    English
    Spanish
    Japanese
}

/// A greeting in a given language.
struct Greeting {
    message: str
    language: Language
    optional sender: str
}

protocol Greeter {
    function greet(greeting: Greeting) -> bool;
}
```

## Declarations

A schema is a flat list of declarations, in any order:

| Keyword | Purpose |
|---|---|
| [`struct`](structure.md) | a data shape — named, typed [fields](structure.md#fields) |
| [`enum`](enum.md) | a closed set of named variants |
| [`protocol`](protocol.md) | a set of callable [`function`s](protocol.md) |
| [`error`](error.md) | a named failure with an interpolated `message` and fields, raised by functions with `!` |
| [`const`](const.md) | a compile-time constant: `const NAME: type = value` |
| [`use`](use.md) / `import` | pull declarations in from another schema or package |

## Types

Primitives:

| Group | Types |
|---|---|
| signed integers | `s8` `s16` `s32` `s64` |
| unsigned integers | `u8` `u16` `u32` `u64` |
| floats | `f32` `f64` |
| boolean | `bool` |
| text | `str` (see below) |

Plus any `struct` / `enum` name (scoped: `pkg::module::Type`), arrays (`Type[]`
or fixed `Type[10]`), and unions (`union(TypeA TypeB)`).

### `str` vs `string` vs `String`

- **`str`** — the text type. Use this. It is what the examples and the
  compiler's diagnostics treat as canonical.
- **`string`** — currently an accepted **synonym** for `str`: it parses,
  validates, and generates identically. The compiler nudges you toward `str`
  (`did you mean 'str'?`). Whether `string` is kept, removed, or given a distinct
  meaning later is unsettled — prefer `str`.
- **`String`** (capitalised) — **not** Comline syntax. It is the Rust type that
  `str` generates into, so you see it in generated Rust, never in a `.ids` file.

## Comments and docs

`//` is a comment. `///` lines are [docstrings](docstrings.md) and attach to the
next declaration.

## Imports

```
use std::http::Request
use mypackage::{User, Post}
use external::uuid::Uuid as UUID
use parent::common::*
```

`self::`, `parent::` and `crate::` prefixes resolve relative to the current
schema. `import path` is the older form, still accepted. See [Imports](use.md).
