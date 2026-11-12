# Migrating stored IR across format versions

Status: **draft** · tracked in [core#268](https://github.com/ComlineProject/core/issues/268) · feeds
[core#146](https://github.com/ComlineProject/core/issues/146) (reading older IR after 1.0) and the
[granular `@unverified`](../shared-vocabulary/granular-unverified.md) work, which is IR format 4 · seven parts,
read in this order: [the formats](formats.md), [steps](steps.md), [running a migration](running.md),
[proving it](proof.md), [hashes, pins and history](hashes-and-history.md),
[beyond the local store](beyond-the-store.md), [format 4 as the first client](format-4.md)

**The question.** `.comline/` holds every version a package has had, and compatibility checks, the changelog and
`comline doc --version` all read it. When core changes the shape of what it stores, `ensure_compatible_store`
deletes the directory, so the version history is lost with each bump. **Can every stored format, past and future,
be migrated to the current one, so that nobody can tell the result from a store the current core built, except
where the old format never recorded something, and so that this is shown by tests instead of asserted?**

## What it looks like today

| Part | Today |
|---|---|
| **The stamp** | `.comline/FORMAT_VERSION` holds `CURRENT_IR_FORMAT_VERSION` (3). `ensure_compatible_store` compares with `!=`: anything else, a missing stamp included, deletes all of `.comline/`, `deps-cache/` too. |
| **Who deletes** | `comline build` does it with a warning in the log. The read commands (`diff`, `doc`, `generate`, `inspect`, `release`) refuse, and say that `build` "starts the version history over". An older binary deletes a store that is *newer* than it, because the check is `!=`. |
| **What a number means** | Four on-disk shapes have existed: an unstamped bincode store and formats 1, 2 and 3. Format 3 is not one shape: [twenty additions](formats.md#format-3-is-a-family) have landed in it without a bump. |
| **What the rule is** | Bump only for a rename, a removal or a retype; anything else is "additive". The rule is in a doc comment. Nothing checks it: the commit that introduced the stamp deferred a golden-hash check "if it becomes a real recurring problem". |
| **Hashes that cover IR bytes** | Every object's address, a dependency pin (`hash = "blake3:…"`, scheme v2, [core#261](https://github.com/ComlineProject/core/pull/261)) and `schema_ir_hash`. A format change moves them. |
| **Proof** | Round-trip tests over real packages, an oracle property test and fuzz targets for the guarantee check, differential tests in the runtime. None says anything about an old store. |

Format 3 is the first format with a population of stores worth saving, and the next change, format 4
([core#222](https://github.com/ComlineProject/core/issues/222)), would wipe all of them. This proposal comes first
so that it doesn't.

## What this proposes

1. **[Formats written down](formats.md).** Each format has a document (blobs, trees, entries, field meanings, what
   an absent entry means), frozen copies of its types, and a ledger of every addition made without a bump. The
   additive rule is tightened and checked.
2. **[Steps](steps.md).** A migration is a chain of single steps `N → N+1`. A step is a total, deterministic
   function over frozen format-N types, with a written list of what N cannot know. Those things are written as an
   explicit **unknown**, never as a default that looks complete. Every step also has an inverse witness, so no
   step can drop what a version recorded.
3. **[Running a migration](running.md).** The new store is written beside the old one, verified, and swapped in;
   the old one is kept. A migration can be checked without writing (`comline store migrate --check`), resumed, and
   repeated. A store newer than the binary is an error, never a deletion.
4. **[Proof](proof.md).** A corpus of real stores built by the real historical cores, an equivalence stated field by
   field, differential property tests against an old core, laws (totality, determinism, idempotence, composition,
   hash stability), and a CI gate that fails a format bump without its step, fixtures and document.
5. **[Hashes, pins and history](hashes-and-history.md).** What may and may not change in a hash, how a dependency
   pin survives a format bump without being weakened, and how compatibility and the changelog read a migrated
   history.
6. **[Beyond the local store](beyond-the-store.md).** Every other place stored IR or its hashes appear, and the
   policy for very old formats after 1.0.
7. **[Format 4 as the first client](format-4.md).**

## Rules that hold whatever the details

- **A store is never deleted to change its format.** Migration replaces deletion; where migration is impossible
  the old store stays, and the error says what to do.
- **A step is a pure function of one format's data.** No clock, no environment, no network, no randomness. Two
  people migrating the same store get the same bytes.
- **What a version recorded is kept.** What its format never recorded is unknown, and unknown fails closed
  everywhere it is read: [#251](https://github.com/ComlineProject/core/issues/251)'s rule for a dependency's config,
  and the fail-closed rule of the [shared vocabulary](../shared-vocabulary/granular-unverified.md#fail-closed).
- **Nothing is replaced until it is verified,** and what is replaced is kept until someone removes it.
- **Accurate means tested against a fresh build.** A migrated version equals what the current core would have built
  from the same source, field for field, except for the fields the step declared unknown.
- **A format change brings its step, its fixtures and its document in the same pull request,** or CI fails.

## What is proposed, in one table

| | Proposed |
|---|---|
| Unit of migration | the whole store, version by version, all or nothing |
| Steps | `N → N+1`, typed on frozen copies; `up`, `down` (witness), and a list of unknowns |
| Unknown | typed `Known<T>` where the new type has room, otherwise an `unknown` entry in the root tree that keeps the original value |
| Atomicity | write `.comline.migrating/`, verify, rename the old store to `.comline.format-N.bak/`, rename the new one in |
| Backup | a sibling directory, kept until `comline store prune`; never deleted automatically |
| Newer store | an error naming the format and the comline that reads it |
| Read commands | read an old store through an in-memory migration; they write nothing |
| Pins | verified through the witness: a pin made under format N still verifies if the dependency's content is representable in N |
| History | comparisons recompute derived facts from stored inputs under the current spec; what can't be recomputed is `unseen` |
| Gate | `formats/MANIFEST`, `live ≡ frozen(current)`, fixtures, and a bump check; see [the gate](proof.md#the-gate) |
| Support | formats 1 to 3 migrate; the unstamped bincode store does not, and is refused with options |

## Rollout

Staged pull requests, in the agreed order: the framework, then format 4, then cross-package chains, then tooling.
Each stage is useful on its own, and each is a checklist in [core#268](https://github.com/ComlineProject/core/issues/268).

**1. The framework** (core, format stays 3):

1. *A newer store is an error, not a wipe.* Core and the CLI message. A small pull request, released **before**
   anything ships format 4, so that no binary in circulation deletes a format-4 store.
2. *Format documents and the gate, with no migration yet.* A `formats` crate with the frozen format-3 types, the
   ledger, the seal, the `live ≡ frozen(3)` test, and golden hashes for the fixture packages. This stops further
   no-bump drift before it grows. It also adds, as ledger rows, the two entries nothing writes yet, `unknown` and the
   spec version a version was frozen against, with readers that fail closed, and it ships in a release with step 1
   **before** any step or format that writes either one.
3. *The fixture corpus and its generator,* with format-3 stores built by the historical revs at each ledger row, a
   format-2 and a format-0 store, and the weekly job that proves the old revs still build.
4. *The engine and `comline store`:* container reader, plan, journal, verification, swap, backup, `--check`, with
   the laws proved on a test-only toy format before any real step exists.
5. *Steps 2→3 and 1→2,* each with its fixtures: the first real lossy steps, exercising the unknown machinery.

**2. Format 4** (core): the new frozen shape of [core#222](https://github.com/ComlineProject/core/issues/222) item 3,
step 3→4, its fixtures and format document, and the pin bridge, all in one pull request because the gate requires it.

**3. Cross-package chains** (core): the recomputation of chains over stored dependency IR, `unseen` extended to
chains, and the oracle and the fuzz target run over migrated stores.

**4. Tooling** (CLI, language server, generators, docs):

- `build` and `release` migrate on their own, with the plan printed.
- `doc` caches key on the IR format.
- The language server and `inspect` show `unseen`.
- The guide on [the CAS](../../guides/ir/cas.md) loses its warning about deletion.
- Generators learn what a version with unknowns means.
- `comline store replay` for stores that can't be migrated.

## Still open

Collected from the pages; each is where it is discussed.

- Whether every step needs the inverse witness or only the ones that could lose something
  ([steps](steps.md#the-witness)).
- Whether `build` and `release` migrate by default or need an explicit `comline store migrate`
  ([running](running.md#the-cli)).
- Where the backup lives and for how long, and whether format 4 should also move the store to a new directory name
  so that an older binary can't delete it ([running](running.md#older-binaries)).
- What happens when Git merges two branches whose stores are in different formats
  ([running](running.md#git)).
- Whether a pin that verifies through the witness is accepted silently, with a warning, or only by an explicit
  re-pin ([hashes and history](hashes-and-history.md#pins)).
- Whether to spend the effort on formats 1 and 2, and where the support floor is before and after 1.0
  ([beyond the store](beyond-the-store.md#after-10)).
- Where the frozen formats live: a crate, a module, and whether the IR-only (`wasm`) build carries them
  ([steps](steps.md#where-the-code-lives)).
- Whether a commit should record the core and spec versions that wrote it
  ([hashes and history](hashes-and-history.md#history)).
- What generators and `doc` do with a version that has unknowns ([format 4](format-4.md#consumers)).
- Whether `comline store replay` (rebuilding a history from Git) is worth building for the stores that can't be
  migrated ([steps](steps.md#what-cannot-be-migrated)).
