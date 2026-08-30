# Intermediate Representation

When a schema is compiled, it is lowered to an **Intermediate Representation**
(IR): a flat, structured, language-neutral form of everything the schema
declares. The IR is the thing every later stage works on — it is what gets
stored, versioned, diffed and fed to code generators. Nothing downstream ever
looks at `.ids` source again.

## What it contains

A compiled schema becomes a sequence of **frozen units** — one per declaration:

- `Namespace` — the schema's namespace path
- `Structure`, `Enum`, `Error` — the data shapes, with their fields / variants,
  types, indices and defaults
- `Protocol` — functions with typed parameters and results
- `Validator`, `Settings` — rules and per-schema configuration

The package manifest lowers to units too (`SpecificationVersion`, `Dependency`,
`CodeGeneration`, `PublishRegistry`), so a frozen version carries both the schema
API and the declarations around it.

"Frozen" is literal: a unit is immutable once written, and it is addressed by the
hash of its content.

## Where it goes

`comline build` writes the frozen units into the project's
[content-addressable store](cas.md) under `.comline/`, as one commit in an
append-only chain. Each commit records its tree of units, its parent, an author,
a timestamp and the package version.

Because the store is content-addressed and never rewritten, any past version
stays reproducible, and two versions can be compared unit-by-unit at any time —
that comparison is what drives Comline's
[automatic versioning](../../reference/versioning.md) and `comline diff`.

## Related design notes

- [IR generation & `state.lock`](../../design/ir-generation.md) — the lockfile
  and the auto-versioning rules
- [Consumer generation configuration](../../design/consumer-generation-config.md)
  — what the frozen config does and does not cover
