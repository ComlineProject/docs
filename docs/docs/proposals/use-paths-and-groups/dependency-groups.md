# Dependency groups

Status: **draft** · decided with the user 2026-11-15 · part of [Own schemas, provenance and dependency
groups](index.md)

**The question.** `dependencies` in `config.idp` is a flat table, and a package with a dozen of them has no way to say
which belong together. **Can a package organise its dependencies, for the people reading the manifest and the imports,
without changing what a dependency is called, what a `use` looks like, or any hash?**

## What it looks like

**Decided.** An optional `group` field on each dependency entry:

```idp
dependencies = {
    logging = {
        path = "../platform/logging"
        group = "platform"
    }

    metrics = {
        path = "../platform/metrics"
        group = "platform"
    }

    shared_types = {
        path = "../shared-types"
        group = "team"
    }

    net = {
        version = "1.2.0"
        uri = "https://github.com/acme/net"
        commit = "4f2c9e1"
        hash = "blake3:…"
    }
}
```

- **The table stays flat.** Every dependency is still `dependencies.<name>`, and dependency names stay unique across
  the whole table, groups or not.
- **A group is a label.** A string, written on the entries that share it. An entry with no `group` is ungrouped, and
  there is no group to declare first.
- **Groups never appear in a `use` path.** The imports are `use logging::…` and `use shared_types::…`, exactly as they
  would be without groups. A group name is not a namespace, can equal any name or none, and isn't reserved.

## Presentation only

A group changes how dependencies are shown and ordered, and nothing else. It is **excluded** from:

- the **frozen config's hash**,
- a **dependency pin** (the content hash of `comline-dep-content-v2`, which covers a dependency's schemas and its
  frozen config),
- **compat and config diffs**: moving a dependency to another group, adding a group, or removing one, is no change, and
  has no bump.

So regrouping changes no hash and no history. The simplest way to hold that, and the one that can't drift, is that the
group isn't frozen at all: it is read from the manifest's source by the tools that present dependencies (the CLI and the
language server), the way a comment is. A dependency's own `group`s, in its own `config.idp`, don't reach the consumer
either: the pin already leaves a dependency's `Dependency` units out (`covered_by_pin`), and a test says a regrouped
dependency has the same pin.

Tests that carry this, in core and in the specification's cases: the same package regrouped has the same config hash,
the same pin, the same comparison with its previous version, and is no change to its changelog.

## Order

Groups are ordered by **first declaration**: the order of each group's first entry in the table as written, and not
alphabetically. That means the manifest is read in source order. Core's dependency parse is a map that is sorted to
freeze deterministically, so the order is taken from the syntax tree, not from it.

The formatter uses this to order a file's imports ([import formatting](import-formatting.md)); `comline deps list`
shows dependencies grouped in the same order.

## Commands

**Decided.** `comline deps add` and `comline deps pin` take `--group`:

```bash
comline deps add logging ../platform/logging --group platform
comline deps pin logging --group platform
```

`add` writes the field with the entry it adds, and `pin` sets or changes it on an existing entry, leaving the rest of
`config.idp` as written, as they do for `hash`.

## Alternatives rejected

- **Nested group tables**, `dependencies = { platform = { logging = { ... } } }`. A dependency's entry is itself a
  table, with keys of its own (`path`, `version`, `uri`, `commit`, `hash`): `platform = { path = "..." }` could be a
  group holding a dependency called `path`, or a dependency. The reader and the parser would have to guess, and
  naming a dependency `path` or `hash` would change what the manifest means. Nesting also makes a dependency's address
  depend on its group, which the next point rules out.
- **A separate `dependency_groups` list**, `dependency_groups = { platform = ["logging", "metrics"] }`. It names every
  dependency twice, and the two can disagree (a name in a group that isn't a dependency, a dependency in two groups).
  The user preferred the field: a dependency says what it belongs to where it is written.
