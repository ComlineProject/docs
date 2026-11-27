# Own schemas, provenance and dependency groups

Status: **accepted** · written and decided 2026-11-15 · related:
[core#277](https://github.com/ComlineProject/core/issues/277) (a dependency's protocols on a connection: reach and
numbers recorded in the facts) and [core#268](https://github.com/ComlineProject/core/issues/268) (IR migrations, which
a change to the frozen IR has to go through) · builds on
[A dependency's protocols on a connection](../dependency-protocols/index.md) and
[Migrating stored IR](../ir-migrations/index.md) · four parts:
[relative paths for a package's own schemas](relative-use.md), [provenance](provenance.md),
[dependency groups](dependency-groups.md) and [import formatting](import-formatting.md)

**The question.** A `use` path starts with a word. Today that word can be a schema of the package itself, a
dependency, or `std`, and nothing in the path says which: core and generation tell them apart by how the namespace is
spelled. **Can the language and the tools stop guessing, so that the first segment of a path always names where a schema
comes from, every compiled schema records where it came from, and the dependencies a package has can be organised
and imported in a consistent order?**

## Where things stand

- **A package's own schemas are reached by a bare path.** For `src/types.ids`, a schema writes `use types::User`. The
  same first-segment slot holds a dependency (`use shared_types::foo::X`) and `std` (`use std::http::Request`). Core's
  `ImportResolver` takes `self`, `parent` and `package` first, then `std`, then a name that matches a dependency, and
  anything left is "from the same package".
- **Classification is by spelling, in three places.** A compiled schema is a dependency's when its namespace's first
  segment is a dependency's name or `std`. Core's version history splits a stored version that way
  (`compat::dependency_names`, `Loaded::of`, and the same split in the build's comparison), and generation mirrors it
  (`connections::is_dependency`, [generation#146](https://github.com/ComlineProject/generation/pull/146)).
- **A guard keeps the spelling honest.** A package's own schema whose namespace starts with a dependency's name, or with
  `std`, is a build error ("is named like the dependency 'greeting'", `reject_shadowing_namespaces`,
  [#256](https://github.com/ComlineProject/core/pull/256)): were it allowed, its imports wouldn't be checked and its
  protocols would be filed under the dependency's name. The error is the containment; the rule beneath it is still by
  name, and it makes a perfectly good file name unusable.
- **Dependencies are a flat table.** `dependencies = { name = { ... } }` in `config.idp`, as long as the package needs.
  Nothing says that three of them are the platform's, and two are the team's.

## What this proposes

1. **[Own schemas only through relative paths](relative-use.md).** Within a package, its own schemas are reached as
   `package::…`, `parent::…` or `self::…`. An absolute first segment always means `std` or a dependency. A bare path
   to an own schema is an error at once, with a quick fix: Comline is before 1.0, so there is no deprecation period.
2. **[Provenance, not names](provenance.md).** Each compiled schema records the package it came from: the package
   itself, a named dependency, or `std`. The frozen IR, the generation request and the facts carry it, so nothing infers
   "dependency" from a namespace's spelling. This is a frozen IR change, so it goes through the
   [IR migrations](../ir-migrations/index.md) framework.
3. **[Dependency groups](dependency-groups.md).** An optional `group = "<name>"` on a dependency's entry. The table
   stays flat, names stay unique, and a group never appears in a `use` path. It is presentation only, and no hash or
   history moves when it changes.
4. **[Import formatting](import-formatting.md).** A default order for a file's `use` lines (`std`, the package's own,
   then dependencies by group), configurable in a `[format]` table, read by the language server's formatter and
   any `comline fmt`.

The first two are about what a path and a compiled schema mean, and are needed together: the first makes the author's
side unambiguous, the second stops the tools depending on the author never having made a collision. The last two are
about how a package's dependencies are presented, and ride on the first only in that the order puts the package's own
imports in a tier of their own.

## Decided

Settled with the user (2026-11-15), while drafting and in answer to the open questions:

| | Decision |
|---|---|
| Own schemas | reached only as `package::…`, `parent::…` or `self::…`; an absolute first segment is `std` or a dependency |
| The word for one level up | `parent`, as it is; no `super` synonym |
| Rollout | an error at once, with a language-server quick fix and `comline fix` (rewriting to `package::…`); no edition and no deprecation period, since Comline is before 1.0 |
| Reserved dependency names | `std`, `package`, `parent`, `self` |
| Provenance | recorded per compiled schema (the package, a named dependency, or `std`) in the frozen IR, the generation request and the facts; one canonical namespace form in requests and facts |
| IR format | a bump under the IR migrations framework; it can ride with format 4 or come after it as format 5, whichever is ready |
| Groups | an optional `group = "<name>"` field on each dependency entry; the table stays flat and names unique; never in a `use` path |
| Rejected group shapes | nested group tables, and a separate `dependency_groups` list |
| Groups and hashes | excluded from the frozen config's hash, from dependency pins and from compat and config diffs |
| CLI | `comline deps add` and `comline deps pin` take `--group` |
| Import order | `std`, then the package's own, then dependencies: groups in first-declared order, then ungrouped dependencies; alphabetical within a tier |
| Configuration | a `[format]` table in `comline.toml` (not `config.idp`), for example `imports.order = ["std", "package", "dependencies"]`; the project's configuration, then the defaults, with no per-user override; read by the language server's formatter and any `comline fmt` |
| Groups and `std` | a group orders dependencies only; `std` is always a tier of its own |
| The shadowing guard | stays as it is: a package's own schema named like a dependency, or `std`, is still refused, which also keeps two schemas from compiling to one namespace and one generated file |

## Open questions

None. The six left open in the draft were answered on 2026-11-15 and are in the table above:

1. **Provenance's IR format:** either; it rides with format 4 or comes after it as format 5, whichever is ready.
2. **Where `[format]` lives:** `comline.toml`.
3. **A per-user override:** none. With `[format]` in `comline.toml`, the project's configuration is what formats.
4. **Groups and `std`:** a group doesn't order `std`.
5. **The edition for the error:** no edition. It is an error at once, since Comline is before 1.0.
6. **Equal namespaces:** the shadowing guard stays.

## Rollout

Staged so that each step ships and is useful alone. Nothing here is a tracking issue: the checklist is for whoever
turns the accepted proposal into issues.

1. **specification: conformance cases first.** New compiler cases in `compiler/src`, regenerated into `compiler/cases`
   by `specs/check.sh`, so every implementation reproduces them: a bare path to a package's own schema (the
   error, and the `package::` form clean); a package with a dependency and
   an own schema of the same first word; reserved dependency names; a `group` on an entry, and the same package regrouped
   (the same outcome). A new kind of case for formatting: a schema's text, the configuration, and the text the
   formatter must produce, for the default order, a custom `imports.order`, and groups. New catalog entries for the
   diagnostic codes, per the [shared vocabulary](../shared-vocabulary/index.md).
2. **core: the rule.** The resolver reads an absolute first segment as `std` or a dependency only; a bare path that
   would have reached the package's own schema is an error, with the fix attached; `comline fix` applies it. The reserved names stay as they are
   (`reserved_dependency_name` already refuses `std`, `package`, `parent` and `self`).
3. **core: provenance and the IR format.** Each compiled schema records its provenance; the frozen types, the
   migration step and its fixtures, and the format document, in one pull request as the
   [format gate](../ir-migrations/proof.md#the-gate) requires. `compat::dependency_names`, `Loaded::of` and the split in
   the build's comparison read it instead of the namespace.
4. **core: groups.** The `group` key on a dependency entry, parsed in source order, kept out of every hash and diff,
   with tests that regrouping changes no hash, pin or comparison. The ordering function for imports, in core, so the
   tools that format agree.
5. **generation.** The request carries each schema's provenance and one canonical namespace form;
   `connections::is_dependency` and `reached` read provenance. The `dependencies` list on the request stays, additive,
   until the generators read provenance, then goes.
6. **CLI.** `comline deps add --group` and `comline deps pin --group`; `deps list` shows groups; `comline fix` applies
   the rewrite; `comline fmt`, if and when it exists, reads `[format]`.
7. **language server.** The error with its quick fix to `package::…`; the formatter's import order;
   `[format]` read from `comline.toml`; completion and hover for `group`.
8. **docs.** The [Imports](../../guides/idl/use.md) guide (own schemas, the relative forms, what an absolute path
   means), [Packages & dependencies](../../guides/packages/index.md#dependencies) (groups, `--group`), the
   [`config.idp`](../../reference/package/manifest.md) and [`comline.toml`](../../reference/package/user-configuration.md)
   references (`group`, `[format]`, and the JSON Schema `scripts/sync-comline-toml-schema.py` writes), the
   [CLI reference](../../reference/tools/cli/index.md), and this
   proposal marked accepted.

## Related

- [core#277](https://github.com/ComlineProject/core/issues/277): reach, recorded in the facts. A dependency's protocol
  is reached by a `use`, and which package a protocol belongs to is exactly what provenance records.
- [core#268](https://github.com/ComlineProject/core/issues/268): IR migrations, the framework the provenance change
  goes through.
- [core#245](https://github.com/ComlineProject/core/issues/245) (closed): a dependency's `use` of its own sibling
  schema resolved to the consumer's schema of the same name. The same family of bug, from a bare path meaning
  different things depending on who reads it.
- [generation#146](https://github.com/ComlineProject/generation/pull/146): the request's `dependencies` list and
  `is_dependency`, which provenance replaces.
