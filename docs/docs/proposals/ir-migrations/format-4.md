# Format 4 as the first client

Status: **accepted** · decided 2026-11-13 · tracked in [core#268](https://github.com/ComlineProject/core/issues/268) · part of [Migrating stored IR across format versions](index.md)

**The question.** [Granular `@unverified`](../shared-vocabulary/granular-unverified.md), item 3 of
[core#222](https://github.com/ComlineProject/core/issues/222), changes what a version freezes. What does the 3→4 step
do with every format-3 version already stored, and what is the package author asked?

Format 4 is not designed here. It is the shape that proposal accepted, and this page is what the step does with it.
Anything that depends on the final shape is marked.

**It is the first real client of the system,** and exists to prove it before 1.0, because today's formats won't be
migrated ([scope](index.md#scope-the-system-not-the-history)). One pull request exercises, on a real change: the frozen
copy and ledger, a step with `up`, `down` and an `unknown` list, a typed unknown, the square against a fresh format-4
build, the laws, the pin bridge, and the gate. The test-only formats of [the proof](proof.md#test-only-formats) cover
what one step can't (composition, an untyped unknown); the two together are the system's proof. A format-3 store that
exists when the framework ships is migrated for real (when the user runs `comline store migrate`), and one older than that is not migrated: the user resets it with `comline store reset`.

## What changes

Format 3 freezes what core worked out as a **set**, and where it was written:

- a protocol's `parameters` hold `Unverified(Vec<Guarantee>)` beside the `@unverified` reason, and, since
  [#265](https://github.com/ComlineProject/core/pull/265), markers on arguments, functions, fields and types are
  properties in *their* parameters;
- the package's own `unverified` is a config unit, a `ConfigValue` as written;
- a declared encoding records what it `establishes` and whether it `has_vectors`.

Format 4 freezes, per the decision, **(guarantee, scope path, chain to each cause, reason)**, so that a comparison sees
narrowing and widening and an acknowledgement is pinned to what it covered.

## The step

| Item | In format 3 | In format 4 | What `up` writes |
|---|---|---|---|
| each given-up guarantee | a member of a protocol's set | a record per guarantee | one record per member; the `guarantee` is carried |
| its **scope** | where the marker is written: the protocol, or an inner property since #265 | a scope path | the path of the marker that covers it, read from the stored units. Before #265 only a protocol could carry one, so the protocol is **known**, not guessed |
| the **chain** to each cause | not stored | the hops, package by package | **`Unknown`**, typed, with the reason "format 3 records the set, not the path to its causes" |
| its **reason** | one string on the plain marker, or a dictionary as written | a reason per guarantee | a plain marker's string is copied to each guarantee it covers, as written; a dictionary's entries as written |
| a package-default cause, acknowledged in `config.idp` | the `Unverified` config unit, as written | pinned to the setting that causes it | the unit carried; its pin to the setting is **`Unknown`** |
| a declared encoding's guarantees | `establishes`, `has_vectors`, as they were (the strict reading where absent) | the same | carried |

Two things it does **not** do. It doesn't compute the chains: that needs the guarantee engine and the catalog, which
are live code and change, and a step is frozen. And it doesn't write an empty chain list or a one-hop chain to a
guarantee whose causes weren't recorded; that would read as "no other cause".

The step is `up`, `down` and an `unknown` list, like any. `down` drops the typed unknowns and the scope paths that
equal the old protocol-level reading, and restores the old set, so the witness holds. The `unknown` list is the
two rows above, and the square compares the migration with a fresh format-4 build whose chains and package pins are
forgotten, with each scope that the old format could place left alone.

## Chains in the old versions

Recomputation, not the stored record, answers any question that needs a chain. A version stores its inputs (types,
a dependency's schemas and, since #262, its config), and the current core can compute the chains from those under
the current spec ([history](hashes-and-history.md#history)). So:

- `diff` and the changelog **recompute chains for both versions** and compare those. A migrated version compared with an
  unchanged successor shows no change, even though its stored chain is unknown.
- The chains stay unknown only where an input is missing: a dependency's config in a version older than #262, a type
  whose information an older format never kept. Those are `unseen`, as everything else that can't be seen is
  ([history](hashes-and-history.md#what-a-comparison-does)).
- "Narrowing a marker isn't a major change; widening one or adding a cause is" is a rule over *recomputed* causes for
  these versions, so it needs no stored chain to hold.

## Acknowledgements

Three things are called an acknowledgement, and the migration treats them differently, because only one of them is in
the store:

| | Where it is | At format 4 |
|---|---|---|
| **The author's marker** (`@unverified …`) | the source | Unchanged, and still valid: the plain form acknowledges what core computes at its scope. The frozen record of it is rebuilt by each build |
| **A consumer's acceptance** (`accept_unverified = { Billing = […] }`) | the consumer's `config.idp` | Pinned to chains in format 4. An existing entry is a set and has no pin, so it matches nothing, and the build **asks again**: it refuses, names each protocol, shows what is now recorded (the guarantee, the chain, the origin's reason), and prints the entry. `comline accept` is the existing way to write it |
| **A package's own `unverified = { … }`** | its `config.idp`, next to the setting | Pinned to the setting. The same re-asking applies, once, for a package that wrote it |

This is the intended behaviour of [core#222](https://github.com/ComlineProject/core/issues/222): "a new cause, or a swapped
type upstream, asks again at every hop". A format change that makes every existing acceptance ask once is the same
event, because the pin it lacked is the pin the invariant needs. **Nothing is rewritten.** The CLI has a precedent
that is a good model: when bounds on types arrived, `build` listed every position, and the CLI *offered* package
defaults with maxima the author typed, never guessed
(`bounds_migration.rs`). Here the offer is each acceptance, with what it now covers, and the author decides.

**Decided:** at the 3→4 transition an unpinned `accept_unverified` entry is **re-asked, not accepted**. The build stops and
names `comline accept`, which records the acceptance again with its chain. `config.idp` is never rewritten automatically.
This differs from old dependency pins, which [verify through `down` and are accepted with a notice](hashes-and-history.md#pins):
a pin that verifies through `down` proves the content is unchanged, but an unpinned acceptance proves nothing about which
causes it covered.

## Consumers

What reads a version with unknown chains, and what each does:

| Consumer | With unknown chains |
|---|---|
| `build`, the guarantee check | recomputes from inputs; the unknown is never what it judges on |
| `diff`, `doc --version`, the changelog | recompute; list what is `unseen` |
| `inspect` | shows the recomputed chain, marked "recomputed, not recorded" |
| the generated `@unverified` docs ([generation#93](https://github.com/ComlineProject/generation/issues/93)) | the chain as recomputed. Where it can't be, it fails closed as below |
| a generator, or `doc`, given an old version | **fails closed**: it stops with "unknown (migrated from format N)" for what it would print from an unknown, naming the version and the path. A generator is never handed a placeholder that looks complete |

## Fixtures and tests for 3→4

The corpus ([proof](proof.md#the-fixture-corpus)) needs, for this step: the chain graphs of the oracle, with the inner scopes
(`66feecb`) and the package-scope `unverified` (`9ea142e`), built by format 3's closing core. The square is then: the format-3 store of a graph, migrated, against the format-4 build of
the same graph with chains and package pins forgotten. The differential test draws random graphs and histories from
the oracle's generators, the same ones that test the invariant, so the property that no guarantee goes
unacknowledged is checked over migrated stores too (the cross-package chains part of stage 2 of the rollout).
