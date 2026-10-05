# IDL / Schema

The **Interface Description Language** (IDL, also called the *schema*) is what you
write by hand. A schema file has the extension `.ids` and lives under a project's
`src/` directory. It defines the data shapes and the protocols that carry them,
independent of any language.

```ids
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
| [`settings`](settings.md) | schema-wide switches (`key = value`) — recorded, not yet enforced |
| [`validator`](validator.md) | a named, parameterised field check — recorded, not yet enforced |
| [`use`](use.md) | pull declarations in from another schema or package |

## Comments and docs

`//` is a comment. `///` lines are [docstrings](docstrings.md) and attach to the
next declaration. `//!` lines at the top of a file are its
[module docs](docstrings.md#module-docs).

## Imports

```ids
use std::http::Request
use mypackage::{User, Post}
use external::uuid::Uuid as UUID
use parent::common::*
```

`self::`, `parent::` and `package::` prefixes resolve relative to the current
schema. See [Imports](use.md).
