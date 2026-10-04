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
| relative | `use self::sibling::Type`, `use parent::common::Error`, `use package::root::Type` | resolved against the current schema's location (`package::` is the package root) |

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
name. Paths under `std::` aren't checked yet: std's schemas don't ship with the
toolchain.
