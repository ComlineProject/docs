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
| **major** | a breaking change | removed struct / enum / protocol / error; removed required field; removed variant; removed function; changed a field's type (compared as written); changed a function's argument or return types; added a required field; a removed schema file |
| **minor** | a new feature | added struct / enum / protocol / error; added a variant; added a function; added an optional field; a new schema file |
| **patch** | a modification | a declaration's docstring changed |

The bump applied is the **maximum** over all changes in the build.

Not compared yet ([core#118](https://github.com/ComlineProject/core/issues/118)):
annotations, type aliases, validators, constants beyond their docstring, an
error's fields and ordinal, argument names, a field's `optional` flag, and the
removal of an optional field. Which of these *should* be breaking is under
discussion in [Schema compatibility](../proposals/schema-compatibility.md).

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

A dependency present in both versions is also compared like your own schemas,
and its changes move the bump. They aren't listed in the build's output yet
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
