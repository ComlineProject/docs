# Versioning rules

Comline versions a package **automatically**. Every `comline build` compares the
new schemas against the previous frozen version and bumps the package version by
the largest change it finds. You never write a version by hand — there is no
version field in the manifest; it comes from the
[content-addressable store](../guide/ir/cas.md).

Versions follow [SemVer](https://semver.org/). The first build is `0.0.1`. A
build that changes nothing keeps the version and adds no commit. A change that
takes no bump, such as to `code_generation`, adds a commit at the same version.
`comline diff <old> <new>` runs the same comparison between any two stored
versions on demand.

## Schema changes

| Bump | When | Examples |
|---|---|---|
| **major** | a breaking change | removed struct, enum, protocol, error, constant, type alias or validator; removed field, optional or not; a field's `optional` flipped either way; added a required field (structs and errors); removed or renamed variant (a rename is reported as one); removed function; changed a field's type (compared as written); changed a function's argument names or types, or its return; a function no longer declares an error it did (`!`); an error's ordinal changed; a constant's type changed; a type alias's target changed; a validator's declaration changed; the validators applied to a declaration changed other than by removal (*validation tightened*); `@framing` or `@handshake` changed (writing out the default `comline@1` isn't a change); a protocol gave up a guarantee (`@unverified`, or more given up than before) |
| **minor** | a new feature | added struct, enum, protocol, error, constant, type alias or validator; added a variant; added a function; added an optional field; a function declares a new error; a constant's value changed; validators only removed from a declaration; `@deprecated` added; a protocol gives up fewer guarantees |
| **patch** | a modification | a declaration's docstring changed; a field's default changed; an error's message changed; another annotation changed (`@timeout_ms`, `@idempotent`, `@deprecated` removed or reworded, `@unverified`'s reason reworded, or one core doesn't know) |
| **none** | | a `settings` change |

The bump applied is the **maximum** over all changes in the build. Schema files
are paired by **namespace**, so adding, renaming or reordering files doesn't
compare the wrong schemas: a file that only exists on one side counts as its
declarations being added or removed.

Not compared yet: a type swapped for an alias of the same type is still
reported as a type change
([core#110](https://github.com/ComlineProject/core/issues/110)), a constant's
value counts as minor wherever it's used, and validators reached through a
type alias are compared on the alias, not on each use. The rules being worked
out are in [Schema compatibility](../proposals/schema-compatibility.md).

## Manifest (`config.idp`) changes

Once the frozen config is recorded in a commit, changes to it can also move the
version — but only the parts that describe the schema API:

| Unit | Change | Bump |
|---|---|---|
| `Dependency` | removed, or version changed | **major** (conservative — a dependency's shapes are part of this package's surface) |
| `Dependency` | added | **minor** |
| `SpecificationVersion` | changed | **major** |
| `CodeGeneration` | added / removed / `lang_version` changed | **none** — recorded, never diffed. It is a tooling-capability list, orthogonal to the wire format. |
| `PublishRegistry` | any | **none** — publish metadata |
| `Namespace` | changed | **not a bump** — renaming the package is a new package |

A dependency present in both versions is also compared like your own schemas.
Its changes move the bump, and the build reports them per dependency. The CLI
shows them once it picks this up
([cli#80](https://github.com/ComlineProject/cli/issues/80)).

## History model

The store is an append-only chain of immutable, content-addressed commits —
git-inspired, no branches, never rewritten — so any past version stays
reproducible.

Nothing else holds this history — there is no `publish` yet — so losing
`.comline/` means the next build starts over at `0.0.1`, with no undo.
`comline clean` leaves it alone; only **`comline reset`** deletes it, behind a
typed confirmation (or `--force`). See
[the `clean` / `reset` split](../design/ir-generation.md#the-clean-reset-split).

## Design notes

The rationale, and the open questions (how far the config diff should go,
reproducibility) are in
[IR freezing & the version state](../design/ir-generation.md) and
[Consumer generation configuration](../design/consumer-generation-config.md).
