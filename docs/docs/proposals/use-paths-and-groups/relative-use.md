# Own schemas only through relative paths

Status: **draft** · decided with the user 2026-11-15 · part of [Own schemas, provenance and dependency
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

A bare path that reaches the package's own schema is a deprecation (below). The language server attaches a **quick fix** that
rewrites it to the `package::…` form. `package::` is chosen over the shortest relative form because it is the same
wherever the file sits: moving a schema to another directory doesn't change what its imports say. The qualified
references the import brought in, written with the old spelling, are rewritten with it. `comline fix` applies the
same rewrite to every file.

A path that matches nothing is the error it is today ([When nothing
matches](../../guides/idl/use.md#when-nothing-matches)), with one addition: a bare path whose first segment is neither a
dependency nor `std`, but the name of one of the package's own schemas, is the deprecation, not "no schema matches".

## Rollout by edition

This is the kind of change [editions](../../reference/versioning.md#editions) are for: a form that was valid is no
longer, and the package keeps the old behaviour until it moves.

1. **In the current edition: a warning.** A bare path to the package's own schema warns, in the `deprecation::` family,
   on every use, with the fix attached, and the editor shows it struck through like any deprecated word. Builds pass.
2. **In the next edition: an error.** The same use is `edition::removed`, and `comline fix --edition N` rewrites it
   with the rest of what the edition moves.
3. **Dependencies are unaffected.** A dependency's compiled schemas are frozen with their `use`s already resolved, and
   a package compiled under any edition can depend on one compiled under another.

Which edition number the error lands in is [an open question](index.md#open-questions).

## What stays as it is

- `use shared_types::foo::X`, `use std::http::Request`: a dependency's and `std`'s paths are unchanged.
- The shapes of a `use` (single, whole namespace, `{ ... }`, `*`, `as`) and what they bring in.
- A schema's namespace, which is still its path under `src/`. Only how it is *written in a `use`* changes.
