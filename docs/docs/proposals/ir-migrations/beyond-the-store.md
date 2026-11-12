# Beyond the local store

Status: **draft** · part of [Migrating stored IR across format versions](index.md)

**The question.** The local `.comline/` is not the only place frozen IR, or a hash of it, is kept or relied on. What
does each of the others need, and what does a published package need when there are some?

## Every artifact

| Artifact | Holds | Migration story |
|---|---|---|
| **`.comline/` store** (`objects/`, `refs/`, `FORMAT_VERSION`) | every version, as frozen IR | [Migrated](running.md), whole, with the old one kept; before 1.0, where no step exists, [the user resets it](#the-10-reset) into a backup |
| **`.comline/deps-cache/`** | git checkouts of dependencies: source, not IR | Not migrated, not part of the store. **Carried across the swap**: today's wipe deletes it, and an offline machine can't fetch it again |
| **A dependency's own committed `.comline/`** | its version history; the only thing core reads of it is the newest commit's `version` (`resolved_version`) | Read with the format-independent [container reader](formats.md#what-a-store-holds). Today any failure reads as `0.0.0-unbuilt`; it should say the store couldn't be read |
| **Dependency pins** in `config.idp` | scheme v2 hash over IR bytes | Never rewritten. [Bridged](hashes-and-history.md#pins) |
| **Acknowledgements** in `config.idp`: a consumer's `accept_unverified`, a package's `unverified = { … }` | the set of guarantees accepted, per protocol | Never rewritten. [Re-asked](format-4.md#acknowledgements) when they are pinned to something the old format didn't record |
| **Generated code** | `schema_ir_hash` as the handshake's `ir_hash` | Derived, not migrated: regenerate. The hash follows the units' bytes, so a format change that alters them is visible at a connection. The pull request says so, and the [gate](proof.md#the-gate) lists it |
| **The generator protocol** | each request carries `ir_format` and the frozen units of the schemas | The units a generator gets from an old version are the migrated ones, in the current format. What to do with unknowns: [format 4](format-4.md#consumers) |
| **`comline doc` output and cache** (`.comline-doc.json`) | pages rendered per version, keyed by commit hash and the renderer | Derived. A migration changes commit hashes, so it re-renders once; the key should also hold the IR format |
| **The doc model** (`schemas/doc-model.json`) | a JSON schema, checked by a test | Derived, versioned on its own |
| **The language server, the playground, the editor** | no store; the server resolves dependencies without fetching and excludes `.comline/` from its watching | Nothing to migrate. Each ships a core, and that core's format is what it compiles against |
| **Published packages, the registry** | none yet: [no `publish` step exists](../../guides/ir/cas.md#what-to-commit), the registry server is on hold and core rejects registry dependencies | [Below](#published-packages-and-the-registry) |

There is no `.cmln` archive or equivalent in any repository. Core has a `PublishRegistry` config unit (where a package
publishes) and nothing that builds an archive.

## Published packages and the registry

When there is something to publish, the [offline proposal](https://github.com/ComlineProject/docs/pull/163) already
decides that **identity is the hash and location is replaceable**: a dependency is its pin, and caches and bundles are
keyed by it. The rules for IR follow from that.

- **Migrate on read, never rewrite what is published.** A published archive is addressed by its hash, and perhaps
  signed. Rewriting it is making another artifact. A consumer that meets an archive whose store is in an older
  format reads it through an in-memory migration, as `comline diff` reads an old local store. Its result, if cached, is
  cached beside the archive and keyed by the archive's hash and the target format.
- **An archive says its format outside its payload,** in its manifest, so that a consumer can refuse a newer one
  without decoding it, with the same error as a local store: the format, and the comline that reads it.
- **What a consumer needs from a dependency is its source.** A dependency is compiled from source, and its pin is checked
  against that compile. The stored IR is only for comparing versions (compatibility, the changelog). So a version
  too old to migrate costs a comparison, "can't tell", and never a build.
- **The registry holds, and never migrates.** It serves old archives as they were published. Migration is the
  consumer's, in the consumer's core.
- **A pin never depends on which format an archive's store is in.** That is the requirement the
  [pin bridge](hashes-and-history.md#pins) meets.

## The 1.0 reset

**Decided:** the formats that exist today are all reset when 1.0 arrives, and the numbering restarts: the 1.0 format is
**format 0** of a new numbering, and the first with a guaranteed path forward. Nothing before it is migrated. And, like
everything here, **nothing happens on its own**:

1. **A warning release first.** The release before 1.0 says, once per command that finds a pre-1.0 store, that 1.0 will
   refuse it and which command to run. It changes nothing.
2. **The 1.0 release refuses a pre-1.0 store.** Any command that finds one stops, names `comline store reset`, and
   changes nothing. The reset is the same [user command](running.md#reset) as before 1.0: it renames the store to
   `.comline.format-N.bak/` after the user confirms that exact action, keeps `deps-cache/`, and starts a new store at
   the next build, stamped format 0 of the 1.0 numbering. The backup stays until `comline store prune`.
3. **The stamp has an epoch.** Pre-1.0 stamps are the integers 0 to 4, and a 1.0 `0` or `3` must not be read as one of
   them. So the 1.0 stamp reads `1.0/0`, and a bare integer is by definition pre-1.0.
4. **The frozen types of the pre-1.0 formats are not kept:** the refusal needs only the stamp and the container, which
   are format-independent ([formats](formats.md#what-a-store-holds)).
5. Every format change after it is a step, with a document, fixtures and a seal, as the gate requires. The system is
   already in use by then: format 4's step is its first run.

## After 1.0

[core#146](https://github.com/ComlineProject/core/issues/146) asks that from 1.0 a newer comline reads what an older one
wrote, "either freeze them or keep a reader for every older version, with tests". This proposal is the second: the
framework *is* the readers, and its fixtures and laws are the tests.

| | Before 1.0 | From 1.0 |
|---|---|---|
| **Formats that migrate** | none promised: format 3 for the first client, the rest reset | every format released at or after 1.0, for ever. A released format's frozen types, steps, fixtures and seal are never removed |
| **A store with no path** | refused; the user's `comline store reset` moves it to a backup | refused, and the error names the **bridge release**: the last comline that still migrates it. There is no reset |
| **Dropping a format** | any minor release | a major one, announced one minor earlier; the bridge release stays installable |
| **Cost of a bump** | a step and its fixtures | the same, **and permanent**: it is carried for ever |
| **Additive changes** | a [ledger](formats.md#format-3-is-a-family) row each | a ledger row each, a fixture, and the same lines in the frozen copy |

Because each bump is permanent from 1.0, bumps are worth batching: the policy proposed is that a format bump is
planned, not incidental. Cheap changes are additive ones, and the gate makes those cheap.

A *version* is not a format. Package version 0.3.0, built long ago in a format that still migrates, is migrated like
every version of its store: nothing is dropped, and it can be compared at the precision it recorded, nothing finer.

The spec side needs nothing of this: the spec is append-only for anything frozen
([the vocabulary](../shared-vocabulary/catalog.md#versioning)), so an old version reads under a newer spec without a step.
Only the IR format does.

## Decided here

- **How long a bridge release stays supported is decided at 1.0,** not before.
