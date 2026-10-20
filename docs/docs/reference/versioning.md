# Versioning rules

Comline versions a package **automatically**: the version comes from what
changed, not from a field you write. There is no version in the manifest; it
lives in the [content-addressable store](../guide/ir/cas.md).

## Builds and releases

**Builds** record history; **releases** are the versions consumers see.

- **`comline build`** compares the schemas against the last *release* and
  records a build under a pre-release version: the release it leads to, plus
  a count of builds since the last release. After `0.1.0`, a build adding a
  feature is `0.1.1-dev.1`; a breaking change in the next build makes it
  `0.2.0-dev.2`. The build reports the next release and what calls for it.
  Changes that cancel out between releases cancel out in the bump too. A build
  that changes nothing adds no commit.
- **`comline release`** builds, then creates the version from the **highest
  bump since the last release**. It records the computed bump, the applied
  one and any reason with the release. The first release is `0.1.0`.
- **`--raise <level> --reason "…"`** releases a higher bump than the schema
  shows, for a behaviour change it can't express. A raise the changes already
  reach is recorded as covered, its reason kept as a note. The bump is never
  lowered.
- **`comline release 1.0`** makes a `0.x` package stable, after saying what
  that commits to.

`comline diff <old> <new>` runs the same comparison between any two stored
versions, builds or releases, on demand.

## Before 1.0

Versions follow [SemVer](https://semver.org/), with Cargo's convention before
1.0: while the version is `0.x`, the minor plays the part of the major.

| Change | `0.x` | `1.0` and later |
|---|---|---|
| breaking | `0.3.2` → `0.4.0` | `1.3.2` → `2.0.0` |
| new feature | `0.3.2` → `0.3.3` | `1.3.2` → `1.4.0` |
| modification | `0.3.2` → `0.3.3` | `1.3.2` → `1.3.3` |

Histories from before builds and releases were separate keep their versions,
which all count as releases; from a `0.0.z` release the next one is `0.1.0`.

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
`.comline/` means the next build starts over at `0.1.0-dev.1`, with no undo.
`comline clean` leaves it alone; only **`comline reset`** deletes it, behind a
typed confirmation (or `--force`). See
[the `clean` / `reset` split](../design/ir-generation.md#the-clean-reset-split).

## Design notes

The rationale, and the open questions (how far the config diff should go,
reproducibility) are in
[IR freezing & the version state](../design/ir-generation.md) and
[Consumer generation configuration](../design/consumer-generation-config.md).
