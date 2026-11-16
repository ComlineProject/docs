# Own schemas only through relative paths

Status: **accepted** · decided with the user 2026-11-15 · part of [Own schemas, provenance and dependency
groups](index.md)

**The question.** In `use greeting::hello::Greeting`, is `greeting` the package's own `src/greeting.ids`, a dependency
named `greeting`, or something else? **Can the first segment of an absolute path always mean one thing?**

## The rule

**Decided.** Within a package, its own schemas are reached only through a relative path:

| To reach | Write |
|---|---|
| a schema of this package, from its root | `use package::types::User` |
| the schema one level up | `use parent::common::Error` |
| the current schema, and what is under it | `use self::nested::Type` |
| a dependency | `use greeting::hello::Greeting` |
| the standard library | `use std::http::Request` |

An **absolute first segment always means `std` or a dependency**, never the package itself. The relative forms already
exist and are already documented ([Imports](../../guides/idl/use.md#path-forms)); what changes is that they become the
only way to name the package's own schemas, in every form (a single item, a whole namespace, `{ ... }` and `*`).

```ids
// before: a bare path, which could as well be a dependency's
use types::User
use types::{Order, Customer}

// after
use package::types::User
use package::types::{Order, Customer}
```

The reserved dependency names are **`std`, `package`, `parent` and `self`**. Core already refuses all four as a name
in `dependencies` (`reserved_dependency_name`); this proposal keeps that and says so in the reference, because from now
on the four words are the whole set of first segments that are not a dependency's name.

## Why

Today the first segment is resolved by trying, in order, `self` / `parent` / `package`, then `std`, then a dependency
of that name, and falling through to "the same package". That has three costs.

- **The classification of compiled schemas follows the spelling.** A schema is a dependency's when the first segment of
  its namespace is a dependency's name. A package that depends on `greeting` and also has `src/greeting.ids` has a
  schema that looks like the dependency's. Classified by its spelling, its protocol would be taken for a dependency's:
  it would lose its wire numbers, and compatibility would compare it by reach instead of by what it declares. Core
  refuses to build such a package today (the shadowing guard, [see the index](index.md#where-things-stand)), so the rule is enforced by making a
  file name unusable, and that only for the names the package happens to depend on today: **adding a dependency can
  break a package's own schema**, and which name that is, is none of the schema's business.
- **A bare `use greeting::…` is equally ambiguous to a reader.** Without opening `config.idp` and `src/`, the line does
  not say whether the schema is local, and a package author changing either file changes what the line means.
- **The same ambiguity has already been a bug.** [core#245](https://github.com/ComlineProject/core/issues/245): a
  dependency's `use` of its own sibling schema resolved against the consumer's schema of the same name.

Rust 2018 is the precedent: a path starting with `crate::` is the crate's own, and one starting with a name is an
external crate (or `std`). Comline's word is `package`, since that is the unit it has.

## `parent`, not `super`

**Decided.** The word for "one level up" stays `parent`; `super::` is not added as a synonym. It was suggested because
Rust spells it `super`. One word is kept because:

- `parent` is already in the grammar, in the language's vocabulary, in the [Imports](../../guides/idl/use.md) guide and
  in the language server. Two spellings of one meaning means every tool handles both, the formatter has to pick one,
  and a codebase ends up with both.
- `super` would become a reserved word. A schema or a dependency named `super` is legal today and would stop being,
  which is a breaking change this proposal doesn't otherwise need.
- A namespace is a path of files, not a tree of modules with visibility rules; `parent` says what it is, one level up,
  without borrowing what `super` means in Rust.

## What the editor and the fix do

A bare path that reaches the package's own schema is an error (below). The language server attaches a **quick fix** that
rewrites it to the `package::…` form. `package::` is chosen over the shortest relative form because it is the same
wherever the file sits: moving a schema to another directory doesn't change what its imports say. `comline fix` applies the
same rewrite to every file. The fix changes only the `use`: a qualified reference is written with the schema's namespace
(`types::User`) whichever path reached it, so there is nothing else to rewrite (see [Qualified
references](#qualified-references)).

A path that matches nothing is the error it is today ([When nothing
matches](../../guides/idl/use.md#when-nothing-matches)), with one addition: a bare path whose first segment is neither a
dependency nor `std`, but the name of one of the package's own schemas, is this error, with the fix, not "no schema matches".

## Qualified references

**Decided with the user 2026-11-15: the Rust model,** with the [answers](#qualified-references) below.

> **Built** ([core#290](https://github.com/ComlineProject/core/issues/290),
> [core#297](https://github.com/ComlineProject/core/pull/297), 2026-11-16): `comline check` and `comline build`
> enforce the rule, with the conformance cases in the specification
> ([specification#17](https://github.com/ComlineProject/specification/pull/17),
> [#18](https://github.com/ComlineProject/specification/pull/18)). The
> [Imports guide](../../guides/idl/use.md#referring-to-what-you-imported) says how it reads, and the three
> errors are `reference::not-in-scope`, `reference::qualifier-not-in-scope` and `reference::defined-twice`. Not yet:
> the language server's quick fixes ([language-server#122](https://github.com/ComlineProject/language-server/issues/122))
> and `comline fix` across a package ([cli#162](https://github.com/ComlineProject/cli/issues/162)); and validators,
> constants and thrown errors are still looked up the old way
> ([core#298](https://github.com/ComlineProject/core/issues/298)).

**As built before it (core#285).** A `use` is frozen with its resolved path: `use package::types::User` is `Import("types::User")`.
After it, a field could be written `User` or `types::User`, and a qualified reference had to match a `use` of the file
exactly; `package::types::User` in a type position was not accepted. A type reference was frozen as written. So the rule
above held in `use` lines only: `types::User` in a field looked exactly like a path into a dependency named `types`. It
was always traceable to a `use` in the same file, but a reader couldn't tell from the reference itself.

**The decision.** A qualified reference starts with a name a `use` brought into scope, as in Rust:

| `use` | Then write |
|---|---|
| `use package::types` | `types::User` |
| `use package::types as t` | `t::User` |
| `use package::types::User` | `User` (not `types::User`) |
| `use package::billing::api` | `api::Invoice` |
| `use greeting::hello` | `hello::Greeting` |

`types` in `types::User` is then a name in the file's scope, not an absolute path, and the rule that a bare first
segment means `std` or a dependency holds in `use` lines without an exception elsewhere.

**Fixed with it:**

- This page said the qualified references an import brought in are rewritten by the fix; there were none to rewrite,
  and [What the editor and the fix do](#what-the-editor-and-the-fix-do) now says so.
- `compat` and the sizer resolved a name by namespace suffix and by the first schema declaring it, not as the validator
  does: [core#289](https://github.com/ComlineProject/core/issues/289), fixed with a resolver shared by the three
  ([core#294](https://github.com/ComlineProject/core/pull/294)), which is where the Rust model's rule lives.

**Answered by the user, 2026-11-15:**

1. **A whole-namespace `use` brings in only its name, as in Rust.** `use package::types` puts `types` in scope, and
   nothing in it: a bare `User` needs `use package::types::User`, `use package::types::{User, ...}` or
   `use package::types::*`. A namespace `use` no longer works as a glob too, so a bare name always traces to a `use`
   that names it or ends in `*`.
2. **A full path works in a type position without a `use`, as in Rust.** `package::types::User`,
   `parent::common::Error`, `self::nested::Type`, `std::http::Request` and a dependency's full path
   (`greeting::hello::Greeting`) can be written in a field or parameter with no `use`. Their first segment is
   unambiguous after the rule above: `package`, `parent` and `self` are the package's own, `std` the standard library,
   anything else a dependency.
3. **A path can go down from a name in scope, as in Rust.** After `use package::billing`, `billing::api::Invoice`
   reaches the nested schema `billing::api`.
4. **A qualified reference is frozen as its resolved path,** as a `use` is: `api::Invoice`, `billing::api::Invoice`
   and an alias's `b::Invoice` all freeze as `billing::api::Invoice`. The frozen IR, its hashes and the generators are
   unchanged for existing packages, and tidying a file's `use`s doesn't change them.
5. **A reference the rule refuses is an error at once,** as a bare own-schema path is
   ([core#285](https://github.com/ComlineProject/core/pull/285)): `types::User` after `use package::types::User`, and a
   bare `User` after only `use package::types`. The diagnostic carries the likely rewrite (write `User`, or add the
   `use` that brings the name in), as a quick fix in the language server and across a package with `comline fix`.

## Rollout

**Decided: an error at once.** Comline is before 1.0, so the change doesn't go through an
[edition](../../reference/versioning.md#editions) or a deprecation period.

1. **A bare path to the package's own schema is an error**, with the fix attached, and `comline fix` rewrites every
   file at once.
2. **Dependencies are unaffected.** A dependency's compiled schemas are frozen with their `use`s already resolved,
   so a package can depend on one written before the change.

## What stays as it is

- `use shared_types::foo::X`, `use std::http::Request`: a dependency's and `std`'s paths are unchanged.
- The shapes of a `use` (single, whole namespace, `{ ... }`, `*`, `as`) and what they bring in.
- A schema's namespace, which is still its path under `src/`. Only how it is *written in a `use`* changes.
