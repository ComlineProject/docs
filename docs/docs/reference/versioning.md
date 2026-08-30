# Versioning rules

Comline versions a package **automatically**. Every `comline build` compares the
new schemas against the previous frozen version and bumps the package version by
the largest change it finds. You never write a version by hand — there is no
version field in the manifest; it comes from the
[content-addressable store](../guide/ir/cas.md).

Versions follow [SemVer](https://semver.org/). The first build is `0.0.1`. A
build with no schema changes keeps the version and adds no commit.
`comline diff <old> <new>` runs the same comparison between any two stored
versions on demand.

## Schema changes

| Bump | When | Examples |
|---|---|---|
| **major** | a breaking change | removed struct / enum / field / variant / function; changed a field's type; added a required field |
| **minor** | a new feature | added struct / enum / protocol / error; added a variant; added an optional field; a new schema file |
| **patch** | a modification | a field made optional; a docstring-only change |

The bump applied is the **maximum** over all changes in the build.

## Manifest (`config.idp`) changes

Once the frozen config is recorded in a commit, changes to it can also move the
version — but only the parts that describe the schema API:

| Unit | Change | Bump |
|---|---|---|
| `Dependency` | removed, or version changed | **major** (conservative — a dependency's shapes are part of this package's surface) |
| `Dependency` | added | **minor** |
| `Dependency` | `uri` / `hash` only, same version | **patch** (provenance, not API) |
| `SpecificationVersion` | changed | **major** |
| `CodeGeneration` | added / removed / `lang_version` changed | **none** — recorded, never diffed. It is a tooling-capability list, orthogonal to the wire format. |
| `PublishRegistry` | any | **none** — publish metadata |
| `Namespace` | changed | **not a bump** — renaming the package is a new package |

The `Dependency` arms are implemented but dormant until dependency resolution
lands (`ComlineProject/core` #6).

## History model

The store is an append-only chain of immutable, content-addressed commits —
git-inspired, no branches, never rewritten — so any past version stays
reproducible.

`comline clean` currently **deletes `.comline/` outright** along with generated
code. Nothing else holds the history and there is no `publish` yet, so the next
build starts over at `0.0.1` — with no undo. Treat it as destructive, not
housekeeping; a split into a safe generated-code clean and a guarded
`comline reset` is
[planned](../design/ir-generation.md#comline-clean-is-destructive).

## Design notes

The rationale, and the open questions (how far the config diff should go,
reproducibility) are in
[IR freezing & the version state](../design/ir-generation.md) and
[Consumer generation configuration](../design/consumer-generation-config.md).
