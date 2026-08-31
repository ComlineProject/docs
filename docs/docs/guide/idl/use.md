# Imports

A **`use`** statement brings declarations from another schema or package into the
current file.

```
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
| whole namespace | `use pkg::module` | the module — its items are then referred to qualified (`pkg::module::Type`) |
| multi | `use pkg::module::{A, B, C}` | several items from one module (plain names, no nesting or `as` inside the braces) |
| glob | `use pkg::module::*` | everything in that module |
| relative | `use self::sibling::Type`, `use parent::common::Error`, `use crate::root::Type` | resolved against the current schema's location |

## Referring to what you imported

After a `use`, a type can be written **bare** or **qualified**, Rust-style:

| statement | write the type as |
|---|---|
| `use pkg::types::User` | `User` **or** `pkg::types::User` |
| `use pkg::types::{User, Post}` | `User` / `Post`, or the qualified path |
| `use pkg::types::*` | any name from `types`, bare or qualified |
| `use pkg::types` | `pkg::types::User` (qualified) |
| `use pkg::types::User as Account` | `Account` **or** `pkg::types::User` — **not** bare `User` |

A `use` never shadows a declaration in the current file: a local `struct User`
always wins over `use other::User`.

## Alias

`as NewName` binds the import under a new name for this file:

```
use external::uuid::Uuid as UUID

struct Session {
    id: UUID
}
```

The alias (`UUID`) and the full path (`external::uuid::Uuid`) both work; the
original bare name (`Uuid`) does not. Aliases apply to single-item and
whole-namespace imports, not to `{ ... }` or `*`.

## `import`

`import path` is the older single-item form, kept for compatibility:

```
import std::validators::string_bounds::StringBounds
```

Prefer `use`.
