# Imports

A **`use`** statement brings declarations from another schema or package into the
current file.

```ids
use std::http::Request
use package::types::User
use package::types::{User, Post, Comment}
use package::utils::*
use external::uuid::Uuid as UUID
use parent::common::Error
```

## Which path reaches what

A package's **own schemas are reached only through a relative path**: `package::`,
`parent::` or `self::`. A path that starts with anything else is
**absolute**, and an absolute path always means `std` or a dependency, never the
package itself.

| To reach | Write |
|---|---|
| a schema of this package, from its root | `use package::types::User` |
| the schema one level up | `use parent::common::Error` |
| the current schema, and what is under it | `use self::nested::Type` |
| a dependency | `use greeting::hello::Greeting` |
| the standard library | `use std::http::Request` |

`std`, `package`, `parent` and `self` are reserved: none can be the name of a
dependency, so the four are the only first segments that aren't a
dependency's. `package::` is the same wherever the file sits, so moving a schema
to another directory doesn't change what its imports say.

## Path forms

| Form | Example | Brings in |
|---|---|---|
| single item | `use package::module::Type` | one item by its full path |
| whole namespace | `use package::module` | everything in that module, bare or qualified (`Type` or `module::Type`) |
| multi | `use package::module::{A, B, C}` | several items from one module (plain names, no nesting or `as` inside the braces) |
| glob | `use package::module::*` | everything in that module |
| relative | `use parent::common::Error`, `use self::nested::Type`, `use package::types::User` | resolved against the current schema: `parent::` is one level up, `self::` the schema itself (`self::nested` is a schema under it), `package::` the package root |

The first four rows show `package::`; a dependency's or `std`'s schema takes the
same forms with its own name first (`use greeting::hello::{A, B}`,
`use std::http::*`).

A relative prefix works in every form, including a glob or `{ ... }` straight
after it: `use parent::*` and `use parent::{Error, Page}` import from the schema
one level up (`api.ids`, for a file `api/v1.ids`), and `use parent::common::*`
from the `common` schema beside it. As with any path, one that names no schema,
or an item the schema doesn't declare, fails the build
([below](#when-nothing-matches)).

### A bare path to your own schema is an error

Writing a package's own schema without a relative prefix, in any form (a single
item, a whole namespace, `{ ... }` or `*`, with or without `as`), is an error at
once:

```ids
use types::{User, Post}
```

The build reports it as `import::bare-own-schema-path`, with:

- **message:** `'types::{User, Post}' is one of this package's own schemas, reached by a bare path`
- **context:** ``an absolute path starts with `std` or a dependency's name; 'types' is neither``
- **help:** ``write `package::types::{User, Post}`: a package's own schemas are reached as `package::...`, `parent::...` or `self::...` ``

`comline check` and `comline build` fail on it. The diagnostic carries a quick
fix, titled ``Write `package::types::{User, Post}` ``, that inserts `package::` at
the start of the path. The language server doesn't offer it yet
([language-server#122](https://github.com/ComlineProject/language-server/issues/122)),
and `comline fix` doesn't apply it across a package yet
([cli#162](https://github.com/ComlineProject/cli/issues/162)). Qualified
references the import brought in don't change: they're written with the
schema's namespace (`types::User`) whichever path reached it. A path whose first segment is neither `std`, a
dependency nor one of the package's own schemas is not this error but a
[path that matches nothing](#when-nothing-matches).

## Referring to what you imported

After a `use`, a type can be written **bare** or **qualified**, Rust-style. The
qualified path is the schema's own namespace (`types::User`), not the path the
`use` was written with:

| statement | write the type as |
|---|---|
| `use package::types::User` | `User` **or** `types::User` |
| `use package::types::{User, Post}` | `User` / `Post`, or the qualified path |
| `use package::types::*` | any name from `types`, bare or qualified |
| `use package::types` | `User` **or** `types::User` |
| `use package::types::User as Account` | `Account` **or** `types::User` — **not** bare `User` |

A dependency's schema is qualified by its own path the same way
(`use greeting::hello::Greeting` brings `greeting::hello::Greeting`).

A `use` never shadows a declaration in the current file: a local `struct User`
always wins over `use package::other::User`.

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
| `use typse::User` (no schema `typse`, in the package or its dependencies) | `no schema in this package or its dependencies matches 'typse::User' - did you mean 'types'?` |
| `use package::types::Usr` (`types` has no `Usr`) | `schema 'types' doesn't declare 'Usr' - did you mean 'User'?` |

Both are `import::unresolved`. `use types::User`, with `types` one of the
package's own schemas, isn't one of them: it's the
[bare own-schema path](#a-bare-path-to-your-own-schema-is-an-error) error, which
says to write `package::types::User`.

The editor reports the same unresolved-path errors as you type, with a quick fix
to the closest name. A `std::` path is checked the same way, against the
[standard library](#the-standard-library):
`std has no schema matching 'std::htp::Request' - did you mean 'std::http'?`

## The standard library

`std` is built into the toolchain. Every package can `use std::…` with nothing
in `config.idp`, and the editor and the playground know it too.

| Schema | Declares |
|---|---|
| `std::http` | `HttpMethod` (enum: `GET`, `POST`, `PUT`, `DELETE`), `Request` (`method`, `uri`: at most 8192 characters), `Response` (`status_code`) |
| `std::validators` | the [validators](validator.md#the-standard-validators) `NonEmpty`, `MinChars`, `MinItems`, `IntRange` and `StringBounds` |

```ids
use std::http::Request
use std::validators::{NonEmpty, MinChars}

struct Call {
    request: Request
    @validators = [MinChars(min = 1)]
    label: char[max 64]
    @validators = [NonEmpty]
    tags: char[max 16][max 8]
}
```

`std` and each of its modules carry [module docs](docstrings.md#module-docs):
hover `std` or `validators` in the editor to read them, with what's in each.

The full reference is on this site, [rendered from those docs](../../reference/package/schema/std/index.md)
by [`comline doc`](../documenting.md): [`std::http`](../../reference/package/schema/std/http.md) and
[`std::validators`](../../reference/package/schema/std/validators.md), each declaration with its fields
and variants.

A build includes only the std schemas a package imports. Like a dependency's,
they're frozen into its versions and generated with its own code
(`std/http.rs`). A package that doesn't use std is unaffected. std's version is
the toolchain's.
