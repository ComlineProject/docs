# Proving a migration

Status: **draft** · part of [Migrating stored IR across format versions](index.md)

**The question.** "The migration is accurate" has to be a statement a test makes, for every old format and every
future one, and a format change has to be unable to land without the tests that make it. What are they?

## What accurate means

A migrated version has to be what the current core would have built from the same source, except where the old
format could not know something. As a square that must commute:

```text
                     a package's source, at each point in its history
                 ┌────────────────────┴────────────────────┐
     build with the core of format N              build with the current core (format C)
                 │                                         │
          a store of format N                       a store of format C
                 │                                         │
          migrate  N → C                            forget  N → C
                 │                                         │
                 └──────────────── must be equal ──────────┘
```

`forget` is not a second implementation of the step. It acts on a *current* value and does one thing: it replaces the
paths on the steps' `unknown` lists with an unknown, as `up` would have, and touches nothing else. It is derived from
the lists, so it is a few lines whatever the format. Three kinds of mistake each break the equality:

| The step | The equality fails because |
|---|---|
| computes a wrong value for a field N could know | migrated has a value, forget leaves the fresh one, and they differ |
| invents a value for a field N could not know | migrated has a value, forget has an unknown |
| writes an unknown for a field N could know | migrated has an unknown, forget leaves the fresh value |

## What is compared

Equality is on **root trees**, not commits. A tree's hash covers everything in it, so equal tree hashes are equal
bytes, and the bytes are canonical (CBOR with ordered maps, the same value always encodes the same). It is compared
per part:

| Part of a version | Compared | Why |
|---|---|---|
| `schema_<n>` trees, `config`, `docs`, a dependency's `schema_<n>`, `config` and `dependency_configs` | **exactly,** after `forget`, as bytes | what the format records |
| a path on a step's `unknown` list | the migrated placeholder and `unknown` entry against `forget`'s | N never recorded it |
| `facts` | **exactly,** except the differences in the fixture's `known-differences.toml` | a record of what the build computed under the rules then; a rule that changed since moves a recomputed fact, and the file names the commit that changed it |
| a commit's `version`, `release` and parent structure | exactly, through the old-to-new map | user data |
| a commit's `author`, `timestamp`, `message` and its **hash** | **not compared** | provenance the fresh build can't share: a different time and user, and the hash follows from them |
| a dependency's `manifest` | not compared with the fresh build; compared with the **old** store's | it records the content hash verified at build time, under the pin scheme then in force |
| `deps-cache/`, backups | not part of a store | |

For the comparison to be fair, a fixture's history must be one on which today's rules number the versions as the
old core did. Where they don't, the fixture records why. That is the proof's one admitted gap, and it is a list a
reviewer reads.

## The fixture corpus

**The sources.** A fixed set of packages, committed once and never edited except to add:

- `tour`, the schema in `core/tests/cas/ir_roundtrip_tests.rs` that uses every construct the grammar has;
- the packages in `core/tests/fixtures/packages`, and `std`;
- a package with `//!` headers;
- a package with a path dependency that declares encodings, a `wire`, `unverified` and `settings`, and one whose
  dependency has a dependency of its own (so `dependency_configs` is there);
- packages with `@unverified` at each scope and with `handshake = "none"`;
- the chain graphs of the oracle ([core#244](https://github.com/ComlineProject/core/pull/244)): A's type reached by B, reached by C.

Each is a **scripted history**: snapshots of the sources and the actions between them (`build`, `release`,
`build --reconcile`), with at least a breaking change, a release, a rebuild that changes nothing (so makes no
commit), and, for one package, two heads left by a Git merge. They live in `core/tests/migrations/corpus/`.

**The stores.** For each format that has a step out of it, the real `.comline/` that the real core of that format built
from each script, committed under `core/tests/migrations/stores/format-<N>/<package>/`, with a `PRODUCED_BY` file (the
revision, the digest of the lockfile, the toolchain, the command). A store is a few objects per version, so the corpus
stays small. A format that gains a [ledger row](formats.md#format-3-is-a-family) while it is current gets a second set
for the row, so a store of each level is covered.

Before 1.0 the only format with a step out of it is 3, for the 3→4 client: its fixtures are built by the core at the
closing revision of format 3, the one the framework ships on. The CLI revision that pins it is the easy route,
because the CLI keeps a committed `Cargo.lock`. From 1.0 on, **every released format** gets its fixtures when it
is released, built by that release's core, and keeps them for ever ([after 1.0](beyond-the-store.md#after-10)).

### Regenerating

`cargo xtask ir-fixtures --format N` checks the recorded revision out into a worktree outside the repository, builds
it with its lockfile and `--locked`, and runs each script. Core's only non-determinism is the author (`USER`, or
`whoami`) and the timestamp (`SystemTime`), so the generator sets the first and runs under a fake clock
(`faketime`, on Linux). A store regenerated that way is **byte for byte** the committed one, and `--check` says so.
The committed bytes are the fixtures; regeneration is what shows they are what that core made. A weekly job runs
`--check` for every recorded format, so a yanked crate or a vanished revision shows within a week and not when a
fixture is needed. The committed stores don't depend on it.

Producing a format's fixtures is therefore part of releasing a format, and the [gate](#the-gate) requires them.

### Test-only formats

Format 4 alone can't prove everything: it has one step, and its unknowns are typed. The harness also has formats that
exist only in the test tree, `T0 → T1 → T2`, with real frozen types, codecs and steps, never written by a release:

| What | How it is built in | What it proves |
|---|---|---|
| a chain of two steps | `T0 → T1` and `T1 → T2`, run alone and composed | the **composition** law, N→N+2 against N→N+1→N+2 and against the square |
| a lossy step | `T1` retypes a field so that `T0`'s value can't be recovered, and the new type has no unknown variant | the `unknown` entry, the placeholder, the original kept, and `forget` |
| a typed unknown | `T2` adds a `Known<T>` field | the typed carrier, and that every reader has to handle it |
| a step that is wrong on purpose | each of the three mistakes in [the square](#what-accurate-means), and a step that drops a field or uses a clock | the harness **fails**: the gate is tested by seeing it reject a bad step |
| crashes | the engine on `T0` stores, killed after every write and rename | resume and idempotence |

They need no old cores: a `T0` store is built by the `T0` writer in the test tree. They are the way the system is proven
before there is a second real format.

## Differential property tests

Fixtures are fixed histories. The differential test draws random ones.

- **The generator** is `core/oracle`, extended: `Spec` already renders a package graph to `config.idp` and `.ids`
  files and has no dependency on core. Add **histories**: a sequence of edits (add a field, swap a type, add or
  remove a dependency, change a handshake or a bound, release), with proptest strategies for the property tests
  and `Arbitrary` for the fuzzer, as for the guarantee oracle.
- **The old side runs out of process.** The CLI (or maker) built at the recorded revision of the previous format is run over the
  rendered package, and its `.comline/` is read back. The binary is built once per `(revision, lockfile, toolchain)`
  and cached in CI. The only exchange is the file system.
- **The current side runs in the test:** the current core builds the same history, `migrate` runs on the old store, and
  the two are compared as [above](#what-is-compared).
- **Budget:** 256 cases by default, like the oracle test, and a few per PR if that is too slow to run on each; more
  nightly (`PROPTEST_CASES`). A failure shrinks to the shortest history that disagrees, and the test writes it as a new
  corpus entry.

### An old core as a renamed dependency

The brief asks whether the old core can be a renamed dev-dependency, `comline-core-v3 = { package = "comline-core",
git = …, rev = … }`, so the test calls it in process. Cargo allows two sources of one package under different names.
**It is feasible, and I'd not use it**, for these reasons, none of which has been tried:

- Both parsers are linked into one test binary. If a generated grammar exports C symbols that don't depend on the
  revision, they collide at link time. Core's `Cargo.toml` mentions `tree-sitter-c2rust`, a pure-Rust variant, so this may not
  occur, but it needs trying.
- Core has no `links` key, but its dependencies might, and the resolver unifies versions and features across both
  copies. Old revisions have no lockfile, so they resolve against today's, which is the problem fixtures solve.
- Every old rev wants its own toolchain, and `HEAD` pins `1.99.1`.
- The harness is per revision: the build entry points changed between them (`process_changes`, `build_with`, the
  `deps` feature).
- The test links one more copy of core per format, forever.

Out of process costs a process spawn per version and removes all of it. If the in-process route does work for the
latest format, it can replace the binary for that one.

### A fuzz target

`store_migrate` in `core/fuzz`, in the nightly matrix beside `unverified_oracle`: arbitrary bytes go through each
format's codec and the chain. It must never panic; it may return an error only when the bytes don't decode; and when
they do, the result must encode, decode, and satisfy the witness. A second form draws values of the frozen types
with `Arbitrary`, which covers what no real build produces, and is how totality is tested over the whole format.

## Laws

| Law | Statement | Tested by |
|---|---|---|
| **Totality** | `up` returns a value for every decodable `Version_N`, and it encodes | the `Arbitrary` form of the fuzz target and a proptest over frozen N types, not only reachable ones; every fixture |
| **Determinism** | the same input gives the same bytes on any platform, thread count and version order | run twice and compare; migrate the fixtures on Linux, macOS and Windows and compare digests with committed golden ones; shuffle version order and threads |
| **Information preserved** | `down(up(v)) = v`: no step dropped anything | the witness, over fixtures and random values, and on every real store at [run time](running.md#verifying) |
| **Idempotence** | migrating a migrated store changes nothing; an interrupted migration, resumed, gives the same files | run twice; fault injection that crashes after each write and each rename, then resumes |
| **Composition** | `migrate(N→K) = migrate(M→K) ∘ migrate(N→M)`, and equals `forget` over a fresh build | for each `N < M < K`: migrate to M, write it, continue; compare with straight through, and with the square |
| **Hashes carried** | a payload with the same bytes keeps its hash; each protocol's `shape_hash` and `param_hash`, its wire numbers, and every `version` and `release` are the same after | compare through the old-to-new map |
| **Convergence** | two independent migrations of one store give the same files | different thread counts and order, compared byte for byte |
| **Pins** | a dependency's pin made by the old core still verifies through the witness, or the format change declares that it doesn't | golden pins per format, [below](hashes-and-history.md#pins) |

## The gate

A format change that has no step, no fixtures or no document can't merge. It is a set of checks, most of them
running on every pull request because the stores are committed:

| Check | Fails when |
|---|---|
| **Seal** | a sealed format's directory differs from `formats/MANIFEST`, so a frozen type, a codec or a schema document changed after its format was superseded |
| **`live ≡ frozen(current)`** | the core's types and the frozen copy of the current format encode differently, or can't decode each other's, for a fixture or a random value |
| **Golden fresh build** | a fresh build of each fixture source has different tree hashes from `expected/`, unless the pull request adds a [ledger](formats.md#each-format-is-written-down) row (and the frozen copy) or bumps |
| **Bump check** (`xtask check-format-bump`) | `CURRENT_IR_FORMAT_VERSION` changed, and the pull request lacks any of: `formats/v<C>/` with its four files; a step `C-1 → C` with `unknown`, `up` and `down`; fixtures for every ledger row of `C-1`; the previous format's seal in the manifest; a row in the CAS guide's stamp table |
| **The square, the laws** | any of the above tests fails. A step with no tests can't be there: the bump check requires the fixtures, and the square runs on them |
| **Pin gate** | a golden pin of a fixture dependency moved, and the pull request doesn't declare it ([hashes](hashes-and-history.md#pins)) |
| **Spec** | the vendored spec files differ from `tests/spec/REV`: the existing check, because a step's `forget` reads the catalog |

What it catches:

| The mistake | Caught by |
|---|---|
| A field renamed or retyped without a bump | the fixtures of the current format stop decoding; `live ≡ frozen` |
| A field added without `skip_serializing_if` | the golden fresh build moves for a package that doesn't use it, so a row (and a pin note) is required |
| A bump without a step, or a step without fixtures | the bump check |
| A wrong, invented or needlessly unknown value | the square |
| A field dropped | the witness |
| A `HashMap`, a clock or a thread in a step | determinism and convergence |
| An edit to a frozen format | the seal |

The seal and the bump check should be under CODEOWNERS, and a seal can be moved only by a command that names why, so that
moving one is a deliberate edit and not a side effect. Weekly: the fixtures `--check` against their recorded revisions. Nightly:
the differential test at a larger budget and the fuzz target.

## What this proves, and what it doesn't

It proves that on the corpus and on generated histories, each step does exactly what its `unknown` list says: it
derives what N knew, and nothing else, and it loses nothing. It does not prove it for a store the corpus doesn't
resemble.

The trust base is small and named: the frozen types (each fixture is decoded and re-encoded to the same bytes, which
checks the copies against what real cores wrote), the `unknown` lists a reviewer reads, the old cores built from
their revisions, and the generator's reach. The ledger's granularity is the corpus's: a store written between two
rows by an unreleased build is in no fixture, and a row is added when one is found. `comline store verify` runs
the structural checks on the store of anyone who runs it, which is how a store the corpus didn't predict gets found.
