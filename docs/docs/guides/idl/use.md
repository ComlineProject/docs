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
| single item | `use package::module::Type` | the item, as `Type` |
| whole namespace | `use package::module` | only the name `module`, to qualify with: `module::Type`, and no bare `Type` |
| multi | `use package::module::{A, B, C}` | several items from one module, each by its name (plain names, no nesting or `as` inside the braces) |
| glob | `use package::module::*` | every item in that module by its name, and not `module` itself |
| relative | `use parent::common::Error`, `use self::nested::Type`, `use package::types::User` | resolved against the current schema: `parent::` is one level up, `self::` the schema itself (`self::nested` is a schema under it), `package::` the package root |

The first four rows show `package::`; a dependency's or `std`'s schema takes the
same forms with its own name first (`use greeting::hello::{A, B}`,
`use std::http::*`). What each form brings in decides how a type is written
afterwards: see [Referring to what you imported](#referring-to-what-you-imported).

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
([cli#162](https://github.com/ComlineProject/cli/issues/162)). The fix changes
only the `use`. A path whose first segment is neither `std`, a
dependency nor one of the package's own schemas is not this error but a
[path that matches nothing](#when-nothing-matches).

## Referring to what you imported

A type is written with a name that is **in scope**, as in Rust. A schema has in
scope:

- what it declares itself;
- what its `use` lines bring in (the table below);
- the roots `package`, `parent`, `self` and `std`, and each dependency's name.

| statement | brings in | write the type as |
|---|---|---|
| `use package::types::User` | `User` | `User` |
| `use package::types::{User, Post}` | `User` and `Post` | `User` / `Post` |
| `use package::types::*` | every name in `types`, not `types` | `User` |
| `use package::types` | `types`, and nothing in it | `types::User` |
| `use package::types as t` | `t`, and nothing else | `t::User` |
| `use package::types::User as Account` | `Account`, and nothing else | `Account` |

A whole-namespace `use` brings in only its name, so the names in the namespace
are qualified with it, and a bare name needs a `use` that names it or ends in
`*`. The other way round, an item `use` brings in the item and not the
namespace it came from: after `use package::types::User`, `types` is not in
scope.

```ids
use package::types
use package::types::Order

struct Account {
    owner: types::User   // `types` is in scope
    last: Order          // `Order` is in scope
}
```

A dependency's schemas follow the same rule. `use greeting::hello::Greeting`
brings in `Greeting`, `use greeting::hello` brings in `hello`
(`hello::Greeting`), and `use greeting` brings in the dependency's own name
(`greeting::hello::Greeting`).

### Full paths without a `use`

A path that starts at a root works in a type position with no `use` at all:

```ids
struct Account {
    owner: package::types::User
    failure: parent::common::Error
    detail: self::nested::Type
    request: std::http::Request
    greeting: greeting::hello::Greeting   // a dependency's path
}
```

`parent::` and `self::` mean what they mean in a `use`. The first segment says
where the type comes from: `package`, `parent` and `self` are the package's
own, `std` is the standard library, and any other name is a dependency. A path
to the package's own schema has to start at one of the three:
`shapes::types::User` is refused
([`reference::qualifier-not-in-scope`](#the-errors)), and the fix is
`package::shapes::types::User`.

### Walking down from a name in scope

A path can go down from a name in scope. After `use package::billing`, the
schema `billing/api` is reached as `billing::api::Invoice`; after
`use package::billing as b`, as `b::api::Invoice`. The walk starts at a name a
`use` brought in, so after `use package::billing`, `api::Invoice` is refused:
`api` is not in scope. Write `billing::api::Invoice`, or add
`use package::billing::api`.

### One type, however it's written

A qualified reference is compiled as its path from the package's root:
`api::Invoice` after `use package::billing::api`, `billing::api::Invoice` after
`use package::billing`, `b::Invoice` after `use package::billing::api as b`
and `package::billing::api::Invoice` with no `use` are all
`billing::api::Invoice`. Which way you write a reference doesn't change the
compiled schema, its hashes or the generated code, and tidying a file's `use`
lines doesn't either.

### Defined twice

A name means one thing in a file. A `use` that brings in a name the file also
declares, or two `use` lines that bring in the same name, is an error
([`reference::defined-twice`](#the-errors)); a local declaration no longer wins
quietly over an imported name. Rename one, or import with an
[alias](#alias):

```ids
use package::billing::api::Invoice as BillingInvoice

struct Invoice {
    total: u64
}

struct Account {
    billed: BillingInvoice
    own: Invoice
}
```

A name that comes from a `*` gives way to a declaration or another `use` of
it, as in Rust, and two `use` lines of the same item aren't an error.

### The errors

A reference the rule refuses is an error at once, and the diagnostic gives the
likely rewrite as its fix. Every one is reported, not only the first (and a
file's bad `use` and its bad references together), and the schema then stops
there, so `validate::unknown-type` is never added on top of what they said.

| Code | When | Fix |
|---|---|---|
| `reference::not-in-scope` | a bare name nothing in the file brought in: `User` after only `use package::types`. A namespace written as a type (`types`) is this error too | add `use package::types::User`, or write `types::User`. The help says which schema declares the name; the quick fix is offered when exactly one does, and when none does the help says nothing declares it |
| `reference::qualifier-not-in-scope` | the first segment of a qualified name isn't in scope: `types::User` after `use package::types::User`, or after `use package::types as t` (the alias replaces the name) | write `User`, or `t::User`, or add `use package::types` to keep `types::User`, or write the path from `package` |
| `reference::defined-twice` | a name a `use` brings in and the file declares, or two `use` lines bringing in the same name | rename one, or import with an alias: ``use package::billing::api::Invoice as BillingInvoice`` |

```ids
use package::types::User

struct Account {
    // reference::qualifier-not-in-scope: `types` isn't in scope, write `User`
    owner: types::User
}
```

```ids
use package::types

struct Account {
    // reference::not-in-scope: add `use package::types::User`, or write `types::User`
    owner: User
}
```

A name nothing declares, and a qualifier that matches nothing, are the same two
errors; only the fix differs, as there is no `use` to add. The diagnostics
carry the rewrite as a quick fix. The language server doesn't offer these yet
([language-server#122](https://github.com/ComlineProject/language-server/issues/122)),
and `comline fix` doesn't apply them across a package yet
([cli#162](https://github.com/ComlineProject/cli/issues/162)).

The rule is for the names of types. The validators a field names in
`@validators`, constants in values and sizes, and the errors a function throws
are still looked up the old way, where a whole-namespace `use` brings in every
name
([core#298](https://github.com/ComlineProject/core/issues/298)).

## Alias

`as NewName` binds the import under a new name for this file, **in place of**
the original:

```ids
use external::uuid::Uuid as UUID

struct Session {
    id: UUID
}
```

The alias (`UUID`) and the full path (`external::uuid::Uuid`, a dependency
being a root) both work; the original bare name (`Uuid`) does not. The same goes
for the package's own schemas: after `use package::types as t`, `t::User` and
`package::types::User` reach the item, and `types::User` is
`reference::qualifier-not-in-scope`, because the alias is what came into scope.
Aliases apply to single-item and whole-namespace imports, not to `{ ... }` or
`*`.

## When nothing matches

`comline check` and `comline build` reject a `use` that matches no schema of the
package or of its [dependencies](../packages/index.md#dependencies), naming the
closest match when there is one:

| `use` | Error |
|---|---|
| `use typse::User` (no schema `typse`, in the package or its dependencies) | `no schema in this package or its dependencies matches 'typse::User' - did you mean 'package::types::User'?` |
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
