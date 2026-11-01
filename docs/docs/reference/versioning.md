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

A build compares each version of the package with the last release and takes
the **largest** bump among the changes. Breaking means **wire or names**: an
old peer and a new one can no longer exchange messages, or a name consumers
refer to (a type, member, alias, constant, generated error variant, protocol
or namespace) disappears.

Types are compared **after resolving aliases**, each version through its own.
Schema files are paired by **namespace**, so adding or reordering files
doesn't compare the wrong schemas; a file that only exists on one side counts
as its declarations being added or removed.

### Rules that depend on the encoding

Some changes break one format and not another. The comparison doesn't list
formats: it reads the facts each encoding's **profile** states (the official
ones are in `core_stdlib/packages/comline/profiles/`, proven by the runtime's
conformance vectors) and applies the **strictest** among the encodings in
play.

- **In play:** each protocol's framing (its `@framing`, else the package's
  `wire.framing`, else `datagram@2`) and the package's format (`wire.format`,
  else `json@1` under JSON-RPC, else `packed@1`), in both versions compared.
  A package without protocols has its defaults in play.
- **Unknown encodings:** one whose profile the comparison can't read (any
  third-party encoding, for now) counts as the strictest.

| Fact | Lenient value | Strict value |
|---|---|---|
| `struct_fields` | `by_name` (`json@1`) | `by_position` (`packed@1`, `msgpack@1`) |
| `unknown_field` / `missing_optional` | `ignored` / `absent` (`json@1`) | `rejected` (`packed@1`, `msgpack@1`) |
| `enum_variants` | `by_name` (`json@1`, `msgpack@1`) | `by_index` (`packed@1`) |
| `calls` (per protocol) | `by_name` (`jsonrpc@1`) | `by_index` (`datagram@1`, `datagram@2`) |
| `errors` | `by_name` (no official framing yet) | `by_ordinal` (every official framing) |

### Fields (structs and error bodies)

| Change | Bump |
|---|---|
| add an optional field | **minor** where every format keys fields by name, ignores an unknown field and accepts a missing optional one (`json@1`); **major** otherwise (`packed@1`, `msgpack@1`), reported as *added optional field* |
| add a required field | major |
| remove a field, optional or not | major |
| required → optional, or optional → required | major |
| reorder fields | none where fields travel by name; major where they travel by position |
| change the type (after resolving aliases) | major, including widening |
| swap the type for an equivalent alias, either way, or one alias for another with the same target | patch, reported as *same type, respelled* |
| change the default | patch |
| change a field's docstring | patch |

### Enums

| Change | Bump |
|---|---|
| add a variant at the end | minor (an old reader can't decode it, so a peer mustn't send it to one) |
| insert a variant before others, or reorder | none where variants travel by name; major where they travel by index (`packed@1`) |
| remove or rename a variant | major (a rename is reported as one) |

### Protocols and functions

| Change | Bump |
|---|---|
| add a function at the end | minor |
| insert a function before others, or reorder | major where the protocol's framing calls by index (`datagram@1`, `datagram@2`); none under `jsonrpc@1` (a new function is minor) |
| remove a function | major |
| rename, add, remove or reorder an argument | major |
| change the return type, or switch between one-way and request/response | major |
| respell an argument or return type through an equivalent alias | patch |
| add an error to `!` | minor (an old client receives it as `Remote`) |
| remove an error from `!` | major (a generated error variant disappears) |
| `@framing` or `@handshake` changes (compared by meaning: writing out the default isn't a change) | major |
| a guarantee given up (`@unverified`, or one more joining the set) | major |
| a given-up guarantee restored | minor |
| the `@unverified` reason changed | patch |
| `@timeout_ms`, `@idempotent` or an annotation Comline doesn't know changed | patch |
| a function's docstring changed | patch |
| a protocol renamed (one removed, one added with the same functions) | major, reported as a rename |

### Errors

| Change | Bump |
|---|---|
| append a new error | minor |
| insert, remove or reorder local errors so that an ordinal changes | major where errors travel by ordinal (every official framing) |
| change the fields | as for fields |
| change the message | patch |

### Constants, aliases and validators

| Change | Bump |
|---|---|
| add a constant, alias or validator | minor |
| remove one | major |
| change a constant's type | major |
| change a constant's value | by what it reaches: a validator argument, *validation tightened* (major); only field defaults, patch; nothing on the wire, minor |
| change an alias's target | major, at the alias and at every use |
| change a validator's declaration (targets, parameters or body) | major |
| a field's **effective validators** change other than by removal | major, reported as *validation tightened* |
| validators only removed from a field | minor (*validation loosened*) |

A field's effective validators are its own plus those on its alias chain, so
switching a field to an alias that carries `@validators` tightens it.

### Annotations, documentation and the package

| Change | Bump |
|---|---|
| `@deprecated` added | minor |
| `@deprecated` removed, or its message changed | patch |
| any docstring, on a declaration or a member | patch |
| `@settings`, or a `settings` block | none |
| a namespace (schema file) renamed (one removed, one added with the same declarations) | major, reported as a rename |

### Dependencies

A dependency counts only as far as the package **reaches** into it: the types
its own declarations use or re-export (fields, arguments, returns, errors,
aliases, validators, imports), and everything those use in turn. That part is
compared with the same rules, and the build lists its changes under the
dependency. A change anywhere else in the dependency doesn't move the
version.

Not implemented yet: `@open` enums (enums don't carry annotations in the
frozen IR yet; [runtime#17](https://github.com/ComlineProject/runtime/issues/17)),
validator arguments resolved against their defaults when comparing effective
sets, and facts for third-party encodings (they count as the strictest until
each version records its encodings' facts). Bumps stay advisory until
`comline@2` checks compatibility at the handshake
([core#119](https://github.com/ComlineProject/core/issues/119)).

## Manifest (`config.idp`) changes

Once the frozen config is recorded in a commit, changes to it can also move the
version — but only the parts that describe the schema API:

| Unit | Change | Bump |
|---|---|---|
| `wire.format`, `wire.framing` | changed | **major** |
| `id` | changed | **major**: it names another package. Adding one where there was none is no change |
| `SpecificationVersion` | changed | **major** |
| `Dependency` | added, removed, or version changed | **patch** on its own: what the package uses of it is compared by reach (above) |
| `CodeGeneration` | added / removed / `lang_version` changed | **none** — recorded, never diffed. It is a tooling-capability list, orthogonal to the wire format. |
| `PublishRegistry` | any | **none** — publish metadata |
| `Namespace` | changed | **not a bump** — renaming the package is a new package |

`comline build` and `comline diff` print every change: the package's own,
each dependency's within reach, the config's, and the bump they call for.

## Compatibility facts

Each version provides what a compatibility-checking handshake
(`comline@2`, [runtime#15](https://github.com/ComlineProject/runtime/issues/15))
needs to compare two peers. Core computes these facts; a handshake chooses
what to do with them. `comline inspect` shows them for the latest build.

| Fact | What it is |
|---|---|
| package id | `id` in `config.idp`: which package this is, whatever its name |
| line | per protocol: the release at which it last had a breaking change |
| since | per function: the release it first appeared in, in its protocol |
| shape hash | per protocol: a hash of what it puts on the wire |
| parameter hash | per encoding: a hash of its name and parameters |

### Line

A protocol's line moves to the release that carries a breaking change to it,
by the rules above. A change counts for a protocol when it changes:

- the protocol itself or one of its functions;
- a declaration the protocol reaches: the types its functions take, return
  and throw, what those use in turn, their validators and the constants
  those validators' arguments name, including a dependency's declarations,
  as far as the protocol reaches into the dependency.

A break anywhere else in the package leaves the line alone. A change to the
package's `wire.format`, `wire.framing` or `handshake` moves every
protocol's line. Renaming a namespace or a protocol doesn't move it, because
neither name travels.

### Since

A function's since is the release in which it was added to its protocol. A
function removed in one release and added back in a later one starts again
from the later release.

### Releases only

Lines and sinces always name **releases**. Before 1.0 a breaking change makes
a `0.x` minor release, so a line names a `0.x.0` version.

- A build carries the facts of the release it leads to: after `0.1.0`, a
  build with a breaking change, `0.2.0-dev.2`, gives the protocols it breaks
  the line `0.2.0`.
- Both are computed against the last release, not build by build, so a
  change a later build undoes doesn't count.
- If `comline release` makes a different version than the builds led to (a
  raised bump, or `release 1.0`), the facts are renamed to the version
  released. A raise isn't a break, so it moves no line, but a function added
  since the last release gets the raised version as its since.

### Shape hash

The shape hash is blake3 over a canonical CBOR encoding of only what reaches
the wire:

- the format, framing and handshake in play, by their parameter hashes;
- the functions in declaration order: names, argument names and types,
  return type, the errors they throw (ordinal, name, fields) and
  `@provider`/`@consumer`;
- every struct, enum and error they reach, with field names, types and
  optionality and variant names, in order.

Aliases are resolved. Each declaration gets a number in the order it is first
reached, so type names don't count. Docstrings, spans, validators, constants,
field defaults, advisory annotations and namespaces are left out. The hash is
computed when asked for, not stored.

### Parameter hash

Each format, framing and handshake in play gets blake3 over the CBOR of its
kind, canonical name and parameters. The parameters are a framing's
`{ name = ..., ... }` entries other than `name`, plus, for an encoding the
package declares in `encodings`, its profile's hash.

### Storage

Lines and sinces need history, so each build records them in its commit as a
`facts` blob beside `config` and `docs`. The schema blobs, `schema_ir_hash`
and generated code don't change. A version built before facts were recorded
gets them computed from its history when read, and recomputing a stored blob
from history gives back the same blob.

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
