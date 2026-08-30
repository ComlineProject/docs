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
| multi | `use pkg::module::{A, B, C}` | several items from one module (plain names, no nesting or `as` inside the braces) |
| glob | `use pkg::module::*` | everything in that module |
| relative | `use self::sibling::Type`, `use parent::common::Error`, `use crate::root::Type` | resolved against the current schema's location |

## Alias

`as NewName` renames the import for this file:

```
use external::uuid::Uuid as UUID
```

## `import`

`import path` is the older single-item form, kept for compatibility:

```
import std::validators::string_bounds::StringBounds
```

Prefer `use`.
