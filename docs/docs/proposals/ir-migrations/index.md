# Migrating stored IR across format versions

Status: **draft** · tracked in [core#268](https://github.com/ComlineProject/core/issues/268) · feeds
[core#146](https://github.com/ComlineProject/core/issues/146) (reading older IR after 1.0) and the
[granular `@unverified`](../shared-vocabulary/granular-unverified.md) work, which is IR format 4 · seven parts,
read in this order: [the formats](formats.md), [steps](steps.md), [running a migration](running.md),
[proving it](proof.md), [hashes, pins and history](hashes-and-history.md),
[beyond the local store](beyond-the-store.md), [format 4 as the first client](format-4.md)

**The question.** `.comline/` holds every version a package has had, and compatibility checks, the changelog and
`comline doc --version` all read it. When core changes the shape of what it stores, `ensure_compatible_store`
deletes the directory, so the version history is lost with each bump. **Can the formats from 1.0 on be migrated, each
to the next, so that nobody can tell the result from a store the current core built, except where the old format never
recorded something, and so that this is shown by tests instead of asserted?**

## Scope: the system, not the history

**Decided (the user, 2026-11-13):** the formats that exist today will all be reset when 1.0 arrives, and the numbering
restarts at format 0. So this proposal prepares **the migration system and shows it is sound**: the model, frozen
per-format types, steps, the unknown and fail-closed machinery, atomic and idempotent running, the laws, the proof
harness and the CI gate. It does not promise to migrate today's formats (the unstamped bincode store, formats 1 and 2,
or the family that is format 3), and it is fine if one of them can't be migrated reliably. The 1.0 format is the first
with a guaranteed path forward.

- **Before 1.0,** a store in an older format with no step to the current one is **never touched by a command on its own.**
  The command stops and names `comline store reset`, which the user runs, and which moves the store to a backup and
  deletes nothing. A store *newer* than the binary is refused. `deps-cache/` is kept. See
  [running](running.md#what-each-command-does-with-each-stamp).
- **The system is proven before 1.0,** because 1.0 must not be its first test. The 3→4 step for the chains of
  [core#222](https://github.com/ComlineProject/core/issues/222) is the first real client, and test-only formats prove
  composition and lossy steps. See [format 4](format-4.md) and [proof](proof.md).
- **The 1.0 reset:** a warning release, then a 1.0 release that refuses pre-1.0 stores and names the reset command. See
  [beyond the store](beyond-the-store.md#the-10-reset).

## What it looks like today

| Part | Today |
|---|---|
| **The stamp** | `.comline/FORMAT_VERSION` holds `CURRENT_IR_FORMAT_VERSION` (3). `ensure_compatible_store` compares with `!=`: anything else, a missing stamp included, deletes all of `.comline/`, `deps-cache/` too. |
| **Who deletes** | `comline build` does it with a warning in the log. The read commands (`diff`, `doc`, `generate`, `inspect`, `release`) refuse, and say that `build` "starts the version history over". An older binary deletes a store that is *newer* than it, because the check is `!=`. |
| **What a number means** | Four on-disk shapes have existed: an unstamped bincode store and formats 1, 2 and 3. Format 3 is not one shape: [twenty additions](formats.md#format-3-is-a-family) have landed in it without a bump, which is why the rule needs a check. |
| **What the rule is** | Bump only for a rename, a removal or a retype; anything else is "additive". The rule is in a doc comment. Nothing checks it: the commit that introduced the stamp deferred a golden-hash check "if it becomes a real recurring problem". |
| **Hashes that cover IR bytes** | Every object's address, a dependency pin (`hash = "blake3:…"`, scheme v2, [core#261](https://github.com/ComlineProject/core/pull/261)) and `schema_ir_hash`. A format change moves them. |
| **Proof** | Round-trip tests over real packages, an oracle property test and fuzz targets for the guarantee check, differential tests in the runtime. None says anything about an old store. |

The next change, format 4 ([core#222](https://github.com/ComlineProject/core/issues/222)), would wipe every store.
This proposal comes first so that it doesn't, and so that by 1.0 the machinery has already carried a real change.

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
   repeated. It runs only when the user runs it: every other command stops and names it. A store newer than the binary
   is an error, never a deletion.
4. **[Proof](proof.md).** A corpus of real stores built by the real core of each format, an equivalence stated field by
   field, differential property tests against the previous format's core, test-only formats for composition and lossy
   steps, laws (totality, determinism, idempotence, composition, hash stability), and a CI gate that fails a format bump
   without its step, fixtures and document.
5. **[Hashes, pins and history](hashes-and-history.md).** What may and may not change in a hash, how a dependency
   pin survives a format bump without being weakened, and how compatibility and the changelog read a migrated
   history.
6. **[Beyond the local store](beyond-the-store.md).** Every other place stored IR or its hashes appear, the 1.0 reset,
   and the policy for old formats after 1.0.
7. **[Format 4 as the first client](format-4.md),** which proves the system end to end before 1.0.

## Rules that hold whatever the details

- **Nothing is deleted or changed without the user doing so.** No command migrates, resets, moves or deletes a store
  as a side effect. A command that finds an older store stops, says what it found and names the command to run
  (`comline store migrate`, with `--check` as the dry run, or `comline store reset`). On a terminal it may ask whether
  to run that exact command and does nothing without a yes; in CI it fails with the message. Backups are removed only by
  `comline store prune`. The one thing a command may do on its own is read an old store through an in-memory migration,
  because that changes nothing on disk.
- **A store is never deleted to change its format.** Migration replaces deletion; where migration is impossible
  the old store stays, and the error says what to do.
- **A step is a pure function of one format's data.** No clock, no environment, no network, no randomness. Two
  people migrating the same store get the same bytes.
- **What a version recorded is kept.** What its format never recorded is unknown, and unknown fails closed
  everywhere it is read: [#251](https://github.com/ComlineProject/core/issues/251)'s rule for a dependency's config,
  and the fail-closed rule of the [shared vocabulary](../shared-vocabulary/granular-unverified.md#fail-closed).
- **Nothing is replaced until it is verified,** and what is replaced is kept until someone removes it. A store that
  can't be migrated stays as it is until the user resets it into a backup.
- **Accurate means tested against a fresh build.** A migrated version equals what the current core would have built
  from the same source, field for field, except for the fields the step declared unknown.
- **A format change brings its step, its fixtures and its document in the same pull request,** or CI fails.

## What was decided

Settled with the user, and written into the pages:

| | Decision |
|---|---|
| Unit of migration | the whole store, version by version, all or nothing |
| Steps | `N → N+1`, typed on frozen copies; `up`, `down` and a list of unknowns. **Every step has the `down` witness**, checked in tests and at migration time on the user's own store |
| Unknown | typed `Known<T>` where the new type has room, otherwise an `unknown` entry in the root tree that keeps the original value. Generators and `doc` **fail closed** on one: "unknown (migrated from format N)" |
| Automatic changes | **none.** Migration and reset run only by the user's command; other commands stop and name it (`comline store migrate`, `--check` as the dry run; `comline store reset`). CI fails with the message |
| Atomicity | write `.comline.migrating/`, verify, rename the old store to `.comline.format-N.bak/`, rename the new one in |
| Backup | `.comline.format-N.bak/`, kept until the user runs `comline store prune` |
| Reset | `comline store reset`, an explicit command that moves the store to a backup after the user confirms that exact action; `deps-cache/` is kept |
| Newer store | an error naming the format and the comline that reads it; never touched |
| Read commands | read an old store through an in-memory migration; they write nothing |
| Git merge of stores in two formats | refused: "migrate both sides first" |
| Pins | verified through the witness; an old pin that verifies is **accepted with a one-line notice** suggesting a re-pin, never silently and never a failure |
| History | comparisons recompute derived facts from stored inputs under the current spec; what can't be recomputed is `unseen`. Each stored version records the core and spec versions that wrote it |
| Frozen formats | the `comline-ir-formats` crate; the IR-only (`wasm`) build carries it only for in-memory, read-only migration |
| Gate | `formats/MANIFEST`, `live ≡ frozen(current)`, fixtures, and a bump check; see [the gate](proof.md#the-gate) |
| Today's formats | not migrated; the user resets them; at 1.0 the numbering restarts |
| 1.0 | a warning release, then a 1.0 release that refuses pre-1.0 stores, names the reset command, and stamps `1.0/0` |
| Bridge releases | how long one is supported is decided at 1.0 |
| First client | the 3→4 step of #222's chains, end to end, before 1.0 |

Binaries from before this proposal delete a store whose stamp they don't expect. They are out of scope.

## Rollout

Staged pull requests: the framework, then format 4 as its first client, then the 1.0 refusal and reset. Each is a
checklist in [core#268](https://github.com/ComlineProject/core/issues/268).

**1. The framework** (core, format stays 3):

1. *A newer store is an error; an older store is an error naming `comline store migrate` or `comline store reset`;
   nothing is changed automatically.* Core and CLI message. This removes the wipe and is released first.
2. *Format documents and the gate.* A `formats` crate with the frozen format-3 types, the ledger, the seal, the
   `live ≡ frozen(3)` test, and golden hashes for the fixture packages. This stops further no-bump drift before it
   grows. It also adds, as ledger rows, the entries nothing writes yet (`unknown`, and the core and spec versions that
   wrote a version), with readers that fail closed, before any step or format writes them.
3. *The engine and `comline store`:* container reader, plan, journal, verification, swap, backup, `--check`, `reset`,
   `prune`, and the prompt a command shows on a terminal.
4. *The proof harness,* proved on **test-only formats** before any real step exists: composition (N→N+2), a lossy step
   with unknowns, the witness, crash injection, the laws. And the fixture generator.

**2. Format 4, the first client** (core): the new frozen shape of
[core#222](https://github.com/ComlineProject/core/issues/222) item 3, step 3→4, its fixtures (stores built by format
3's closing core) and format document, the pin bridge, and acknowledgements re-asked, all in one pull request because
the gate requires it. It runs the square, the laws and the gate on a real change. Then cross-package chains:
recomputation over stored dependency IR, `unseen` extended to chains, and the oracle and fuzz target over migrated
stores.

**3. The 1.0 refusal and reset** (core, CLI): a warning release, then the 1.0 release, which refuses a pre-1.0 store,
names `comline store reset`, and stamps `1.0/0`. From then on every format change is a step. See
[the 1.0 reset](beyond-the-store.md#the-10-reset).

**4. Tooling** (CLI, language server, generators, docs):

- `doc` caches key on the IR format.
- The language server and `inspect` show `unseen`.
- Generators and `doc` fail closed on unknowns.
- The guide on [the CAS](../../guides/ir/cas.md) loses its warning about deletion and describes the stamp, backups and
  `comline store`.

## Still open

Little is left:

- Whether `SCHEMA.md` in core is the source for each format's document, with the CAS guide describing the current format
  ([formats](formats.md#decided-and-open-here)). Leaning yes.
- Whether the 3→4 transition accepts an unpinned `accept_unverified` entry with a warning
  ([format 4](format-4.md#acknowledgements)). Leaning no: the safety invariant is there to remove such an entry.
