# Imports

A **`use`** statement brings declarations from another schema or package into the
current file.

```ids
use std::http::Request
use mypackage::types::User
use mypackage::{User, Post, Comment}
use mypackage::utils::*
use external::uuid::Uuid as UUID
use parent::common::Error
```

## Path forms

| Form | Example | Brings in |
|---|---|---|
| absolute | `use pkg::module::Type` | one item by its full path |
| whole namespace | `use pkg::module` | everything in that module, bare or qualified (`Type` or `pkg::module::Type`) |
| multi | `use pkg::module::{A, B, C}` | several items from one module (plain names, no nesting or `as` inside the braces) |
| glob | `use pkg::module::*` | everything in that module |
| relative | `use parent::common::Error`, `use self::nested::Type`, `use package::types::User` | resolved against the current schema: `parent::` is one level up, `self::` the schema itself (`self::nested` is a schema under it), `package::` the package root |

A relative prefix works in every form, including a glob or `{ ... }` straight
after it: `use parent::*` and `use parent::{Error, Page}` import from the schema
one level up (`api.ids`, for a file `api/v1.ids`), and `use parent::common::*`
from the `common` schema beside it. As with any path, one that names no schema,
or an item the schema doesn't declare, fails the build
([below](#when-nothing-matches)).

## Referring to what you imported

After a `use`, a type can be written **bare** or **qualified**, Rust-style:

| statement | write the type as |
|---|---|
| `use pkg::types::User` | `User` **or** `pkg::types::User` |
| `use pkg::types::{User, Post}` | `User` / `Post`, or the qualified path |
| `use pkg::types::*` | any name from `types`, bare or qualified |
| `use pkg::types` | `User` **or** `pkg::types::User` |
| `use pkg::types::User as Account` | `Account` **or** `pkg::types::User` — **not** bare `User` |

A `use` never shadows a declaration in the current file: a local `struct User`
always wins over `use other::User`.

## Alias

`as NewName` binds the import under a new name for this file:

```ids
use external::uuid::Uuid as UUID

struct Session {
    id: UUID
}
```

The alias (`UUID`) and the full path (`external::uuid::Uuid`) both work; the
original bare name (`Uuid`) does not. Aliases apply to single-item and
whole-namespace imports, not to `{ ... }` or `*`.

## When nothing matches

`comline check` and `comline build` reject a `use` that matches no schema of the
package or of its [dependencies](../packages/index.md#dependencies), naming the
closest match when there is one:

| `use` | Error |
|---|---|
| `use typse::User` (no schema `typse`) | `no schema in this package or its dependencies matches 'typse::User' - did you mean 'types'?` |
| `use types::Usr` (`types` has no `Usr`) | `schema 'types' doesn't declare 'Usr' - did you mean 'User'?` |

The editor reports the same errors as you type, with a quick fix to the closest
name. A `std::` path is checked the same way, against the
[standard library](#the-standard-library):
`std has no schema matching 'std::htp::Request' - did you mean 'std::http'?`

## The standard library

`std` is built into the toolchain. Every package can `use std::…` with nothing
in `config.idp`, and the editor and the playground know it too.

| Schema | Declares |
|---|---|
| `std::http` | `HttpMethod` (enum: `GET`, `POST`, `PUT`, `DELETE`), `Request` (`method`, `uri`), `Response` (`status_code`) |
| `std::validators` | `StringBounds`, a validator with `min_chars` and `max_chars` |

```ids
use std::http::Request
use std::validators::StringBounds

struct Call {
    request: Request
    @validators = [StringBounds(min_chars = 1, max_chars = 64)]
    label: str
}
```

`std` and each of its modules carry [module docs](docstrings.md#module-docs):
hover `std` or `validators` in the editor to read them, with what's in each.

A build includes only the std schemas a package imports. Like a dependency's,
they're frozen into its versions and generated with its own code
(`std/http.rs`). A package that doesn't use std is unaffected. std's version is
the toolchain's.
