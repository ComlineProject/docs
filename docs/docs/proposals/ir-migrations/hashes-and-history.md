# Hashes, pins and history

Status: **accepted** · decided 2026-11-13 · tracked in [core#268](https://github.com/ComlineProject/core/issues/268) · part of [Migrating stored IR across format versions](index.md)

**The question.** A migration rewrites what hashes cover. Which hashes may change, which must not, how does a
dependency pin keep meaning what it meant, and what do compatibility checks and the changelog say about a history
that was migrated?

## The hashes that depend on the IR

| Hash | Covers | Computed | Under a migration |
|---|---|---|---|
| **Object** (blob, tree, commit) | the object's serialized bytes | at write | changes exactly where it has to: [below](#object-hashes) |
| **Dependency pin**, `hash = "blake3:…"` in `config.idp` | scheme v2 ([core#261](https://github.com/ComlineProject/core/pull/261)): the CBOR of every schema's frozen units, and the dependency's frozen config units, sorted, minus `PublishRegistry` and `Dependency` | from a fresh compile of the dependency, checked against the pin | not in the store, **never rewritten**, [bridged](#pins) |
| **`manifest`** blob | the content hash verified when a dependency was vendored, as text | at build | carried verbatim. Nothing in core reads it today |
| **`schema_ir_hash`**, the handshake's `ir_hash` | the CBOR of one schema's units, folded to 64 bits | embedded in generated code | follows the units' bytes. Not stored; generated code isn't migrated |
| **`shape_hash`, `param_hash`** | a protocol's canonical wire shape; an encoding's `(kind, name, params)` | when facts are read | **must not change**: peers negotiate on them |

The last is the point of the table: only the first three are *stored*, and only the first changes by construction.

## Object hashes

A hash covers bytes, and a commit holds its tree's hash and its parents'. So a changed payload changes its blob, every
tree on the way up, its commit, and every later commit, because each holds its parent's hash. `release.since` is a
hash too, and so are the second parents a reconcile leaves.

- **What may change:** a payload whose encoding changed, and everything above it. For a format that touches only
  `schema_<n>` blobs, that is those blobs, the trees above them, and the whole commit chain.
- **What must not:** a payload whose bytes are the same in N and C keeps its hash, and is not rewritten. A step that
  moves one field of one unit changes that unit's blob and no other.
- **Who maps them:** the engine, bottom-up, from the model, where references are [version ids](steps.md#the-model).
  A step author never sees a hash. The old-to-new map is a bijection on commits, and is checked.
- **Outside the store:** a CI log, a note, or `comline doc`'s cache (`.comline-doc.json` is keyed by commit hash) may hold
  an old one. `comline store migrate --map` writes the map, and caches should key on the IR format as well.

## Pins

A pin is hashed from **IR bytes**: `schema_units_cbor` is `to_cbor` of the units. So a format change that alters those
bytes for a dependency changes its pin, and the scheme tag (`comline-dep-content-v2`) doesn't know about the IR format.
Core#261 handled the case of a scheme change, and its message ("this pin was made by an older comline") is the
precedent. A *format* change is the same event with no message, and the earlier format changes very probably did it
(not checked) without anyone being told.

Two things make that unacceptable for migrations. A migration that turns every pin in a repository into a mismatch is a
migration that breaks the build it was meant to save. And the [offline proposal](https://github.com/ComlineProject/docs/pull/163)
makes the hash the identity of a dependency: caches and signed bundles are keyed by it, so a hash that moves with core's
internal format would invalidate both.

**Decided:** a pin made under format N, by scheme S, **still verifies under C when the dependency's content can be
expressed in N**, and a pin is never accepted otherwise.

1. To check a pin that doesn't match, core takes the dependency's compiled model and applies `down` through each step
   back to N. If every step's witness is defined on it, the content has nothing N couldn't record. It encodes the
   result with N's codec, hashes it as scheme S did, and compares it with the pin.
2. **A match is exact or it isn't one.** Equality of the hash, of the content N would have recorded. Nothing is weaker:
   the content has no information the pin didn't cover, so every guarantee the pin gave is still given.
3. **If the content uses something N lacks** (a dependency that now has chain markers, with format 4), the witness is
   not defined, no older pin can match, and the error says what is new: "this pin was made under IR format 3; the
   dependency now records chains that it couldn't have covered. Review it and re-pin: `hash = "…"`". The command that
   writes a re-pin exists already as a request (`comline add --repin`, or the future `update`, core#261).
4. **`config.idp` is never rewritten** by a migration or by this check.
5. Cost is only on a mismatch, as `mismatch_message` is today, and only through the formats that still have steps.

A package that doesn't use what format 4 added therefore keeps every pin through the bump, with no action, and the
tests show it ([proof](proof.md#laws)): `golden-pins.json` holds each fixture dependency's pin as the *historical* core
computed it, and the current core must verify it through the bridge. A package that does use it is asked, once, and
told why.

| | A. Verify through the witness (**proposed**) | B. A pin form independent of the IR | C. Re-pin on every format change |
|---|---|---|---|
| An unchanged dependency, after a bump | keeps its pin | keeps its pin | **every pin breaks** |
| A new scheme | no | yes: a v3, so every pin changes once | no |
| A second definition of "content" to keep in step with the IR | no | yes | no |
| Proof | golden pins from the old cores | golden pins from the form | none needed, and none possible |
| Costs | `down` must be defined on a compile, not only on a stored version | the form must also carry new information the day the IR does | the offline proposal's bundles and caches |

**Decided:** a pin that verifies through the witness is **accepted, with a one-line notice** that suggests a re-pin
("this pin was made under IR format N and still verifies; re-pin to move to the current one: `hash = "…"`"). It is never
silent and never a failure. Accepting is sound by the argument above: the content has nothing the pin didn't cover. The
re-pin is the user's, by hand or with `comline add --repin`; nothing rewrites `config.idp`. Option B stays available if
the bridge turns out too costly to keep through many formats.

The pin gate in [the proof](proof.md#the-gate) makes the move visible: a change that moves the *fresh* pin of a fixture
dependency has to say so in the pull request.

## History

Compatibility, `diff` and the changelog compare versions, and a migrated history is not the same as a freshly built
one in what it records. The principle is:

> **Compare from inputs; recompute outputs; keep what only history can say.**

| What a version holds | Examples | In a migrated history |
|---|---|---|
| **Inputs** | the schema units, the vendored dependencies' schemas and configs, `config`, `docs` | carried. If a version never kept one, it is **unseen**, not empty |
| **Outputs of a rule** | a protocol's given-up guarantees and their causes, the encodings in play, a shape hash | recomputed when read, by the core that reads, under the current spec. Where stored (for pinning an acknowledgement, or to be quick), the stored value is a record and not an input to comparisons |
| **History itself** | `version`, `release` records, a protocol's `line`, a function's `since`, wire numbers | carried as data. They depend on the chain, not one version, and they are promises that peers may already hold |

Version numbers in particular are **kept** even where today's rules would have numbered the history differently. A
migration is not a rebuild, and a version that was released as `0.4.0` was.

### What a comparison does

- **Both sides are recomputed under the same, current spec.** [Granular `@unverified`](../shared-vocabulary/granular-unverified.md#a-newer-spec-that-finds-an-existing-loss)
  says `diff` recomputes both versions under the newer spec, so a loss the spec learned to see is in both and is no
  change. A format-3 version whose protocol never had `bounded_size` in its frozen set (the guarantee didn't exist) is
  not "narrower" than today's: it is recomputed, and gives it up like its successor does.
- **The spec and core that wrote a version** are, today, recorded nowhere: the decision in the vocabulary is that each
  frozen version records the spec it was frozen against, and that isn't built. **Decided:** each stored version records
  **the core version and the spec version that wrote it**, as root-tree entries (absent meaning unknown), in the first
  release of the framework, so every version built after it has them. A version without them, a migrated one included, reads as `unknown`, is
  recomputed under the current spec like any older one, and a ledger row can be told from the record instead of
  guessed.
- **What can't be recomputed is `unseen`.** If a rule needs an input the version lacks (a dependency's config, a
  type's width), the comparison lists it in the same `Comparison::unseen` that [core#262](https://github.com/ComlineProject/core/pull/262)
  added: the version and the path, with the reason from the `unknown` entry. A rule that needs a fact it can't see reads
  the strictest (the same way `Encodings` does when it isn't `complete`), and the bump is **at least a patch**: a
  comparison that couldn't see part of what it compares doesn't say that nothing changed. It can be higher, since
  "strictest" can be a breaking change: a type of unknown width against a known one is possibly breaking.
- **The changelog** shows the same: a change it found, and, as lines of their own, what it could not compare, in the words of
  the reason. `comline doc --version V` for a version with unknowns **fails closed** on what it would print from an unknown, as `doc` does for
  any consumer ([format 4](format-4.md#consumers)).

| Case | Result |
|---|---|
| A package migrated from format 3, source unchanged | Nothing found; see [the first build](#the-first-build-after-a-migration) |
| The spec has since added a guarantee an old protocol gives up | Recomputed on both sides: no change, no false major |
| A version from before dependency configs were kept (core#262) | `unseen: Dependency("acme")`, at least a patch: as now |
| A version that went through a lossy step, with an array whose length was lost, compared to today's | the path listed as unseen; possibly breaking |
| A version whose `release` says `0.4.0` | `0.4.0`, whatever the current rules would number it |

### The first build after a migration

A migrated head lacks what the current core knows, so a fresh build of the unchanged working tree differs from it,
by exactly the unknowns. Without care, the first `comline build` makes a commit, with a bump of at least a patch, to
say that nothing changed.

**Proposed:** the build's "same as before" test compares **modulo unknown**: if the working tree equals the head at
every field the head knows, nothing is committed and no version moves. What the build learned is not written back,
since history is append-only, and is not needed: it is recomputed when read. Any real change is compared with the
unknowns listed as unseen, as above.
