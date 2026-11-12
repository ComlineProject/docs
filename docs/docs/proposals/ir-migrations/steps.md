# Steps

Status: **draft** · part of [Migrating stored IR across format versions](index.md)

**The question.** What is a migration made of, so that it is accurate for every old format, never loses what a
version recorded, and never claims to know what the old format did not?

## The model

A migration moves a whole store from format N to the current format C, one **step** at a time. Steps never touch
bytes or hashes. They work on a **model** of one version, which the format's codec decodes from the store and
encodes back:

```text
bytes ──decode_N──▶ Version_N ──step N→N+1──▶ Version_N+1 ──…──▶ Version_C ──encode_C──▶ bytes
                    (frozen types of N)                          (frozen types of C)
```

A `Version_N` holds the commit's own fields (`version`, `release`, `author`, `timestamp`, `message`), the decoded
payloads (schemas, vendored dependencies, `config`, `docs`, `facts`) and the `unknown` list described
[below](#unknown). A reference to another version, a parent or a `release.since`, is a **version id** (its place in
the chain), not a hash. The engine turns ids back into hashes when it encodes, so a step author never handles a
hash and can't break the Merkle structure. See [hashes](hashes-and-history.md#object-hashes).

The intermediate formats never reach the disk. A store goes from N to C in memory, version by version, and is written
once.

## A step

A step `N → N+1` is three things, written against the frozen types of N and N+1
([formats](formats.md#each-format-is-written-down)), never against today's types:

| Part | What it is |
|---|---|
| `up` | A function from a `Version_N` to a `Version_N+1`. **Total:** it returns a value for every value the format's types can express, not only for what a real build produces. **Deterministic:** the same input, the same output, on every platform. It has no I/O, clock, environment, randomness, thread or hash-map order. Every map in the model is ordered. |
| `down` | The **witness**: a function from the image of `up` back to `Version_N`, with `down(up(v)) = v` exactly. See [the witness](#the-witness). |
| `unknown` | The list of paths in `Version_N+1` that `up` writes as unknown because N never recorded them, each with the reason. Written down in the format's `SCHEMA.md` and read by the tests. |

A step may read only the version it is given and, for facts that live in history, the versions before it in the same
chain. It may not recompute what the *current* core would compute (a guarantee set, a wire number, a shape hash): that
is code that changes, and a step is frozen. What a version recorded is carried across as data, and what has to be
recomputed is recomputed on read, by whichever core is reading. For example the `facts` blob is a record of what
the build computed under the rules in force; a step carries it, and `history_of_commit` already recomputes it when it
is absent or unnumbered.

!!! note "Steps may not delete user data"
    `up` keeps every field of N. A field that N+1 renamed or retyped is mapped. A field that N+1 has no place for is
    kept in the `unknown` list with its original value (see below). The witness checks this.

## Unknown

Where N+1 needs something N never recorded, `up` writes an **unknown**. It never writes a default that looks
complete: a framing the author never chose, a length `T[]` for an array whose length was lost, an empty set of
causes for a guarantee whose causes weren't stored. This is the rule
[core#251](https://github.com/ComlineProject/core/issues/251) set for dependency configs ("read as unknown, never as
defaults that look complete") and the [vocabulary's](../shared-vocabulary/granular-unverified.md#fail-closed) for a
dependency that can't be seen, applied to a whole version.

An unknown has two possible carriers. **Proposed: both**, in this order of preference.

1. **Typed, in the new format.** Where N+1's own type has room for it, the field is `Known<T>`: a value, or
   `Unknown { reason }`. The compiler then forces every reader to handle it. Format 4's chains are the example
   ([format 4](format-4.md#the-step)). A format that adds a field is written so that anything a later step might have
   to leave unknown is already a `Known<T>`.
2. **An `unknown` entry in the root tree,** for a retype whose new type has no room: a blob listing, for each
   unknown, its `path` into the model, the `step` that wrote it, the `reason`, and the `original`, the bytes N
   recorded, where N recorded something. The field itself holds a placeholder that the entry marks as one. This is
   what lets a step exist where the new type has no "unknown" variant and can't gain one without a bump: the entry
   keeps the old value (say, a `float` that N froze without a width) beside a placeholder. Format 3's `TypeRef` is an
   example of a type with no room, and a test-only format has one on purpose
   ([proof](proof.md#test-only-formats)).

`unknown` is an additive entry, a row in format 3's ledger with the absence reading *none*. A version without it
has no unknowns.

**Ordering constraint.** A reader that doesn't know the entry would read a store that carries unknowns as complete. So
the readers of `unknown` ship before any step that writes one. See [the rollout](index.md#rollout).

### Reading an unknown

Consumers don't see the entry or the placeholder. The accessors on a version return `Known<T>`, with no `Deref` and
no default, so an unknown can't be forgotten. Every use then has a rule, and it is the strictest reading:

| A consumer needs | The field is unknown | Result |
|---|---|---|
| a protocol's given-up guarantees | the set or a cause | counts as given up; the build that depends on it refuses |
| a protocol's framing or format | the declaration | the strictest facts, as `Encodings` does when `complete` is false (core#262) |
| a bound | the maximum | unbounded |
| a type, compared | its width or length | breaking, or "can't tell" if the rule has that |
| a span | where it was written | no span; diagnostics name the version instead |
| generating code or documentation | anything the output prints | **fails closed**: the generator or `doc` stops with "unknown (migrated from format N)", [format 4](format-4.md#consumers) |

A comparison that read an unknown says so: it lists the version and the path in the same `unseen` list core#262
added, and its bump is at least a patch. See [history](hashes-and-history.md#history).

Some things are never unknown, because without them a version isn't one: its `version`, its `release` record, its
parents, and the schema units' names. A step that can't produce them fails, and the migration refuses.

## The witness

`down(up(v)) = v` is the proof, on every real version, that a step lost nothing. **Decided: every step has one.** It is
cheap to write for the steps that are likely: one that wraps a value, renames a field or adds a field with an unknown
has a trivial inverse, and a step that moves a value into the `unknown` list keeps the original there so `down` can put
it back. A step that can't state its inverse is exactly the one to look at.

It is checked in two places. The tests run it over fixtures and random values ([proof](proof.md#laws)). And the engine
runs it over every version of **the user's own store** that it migrates, before it swaps anything
([running](running.md#verifying)), so a store the corpus didn't predict is still checked. The witness also has a second
use, for [pins](hashes-and-history.md#pins).

## Chains

`migrate(N → C) = up(C-1→C) ∘ … ∘ up(N→N+1)`. A later step may resolve an unknown an earlier one wrote, only from
data in the version. The unknowns of a chain are the union of its steps' lists minus what a later step resolved,
and the engine writes that list.

The engine has one chain per store and one version at a time. It does not support skipping steps: a "shortcut" from
1 to 3 is a second implementation of the same function, and the composition law ([proof](proof.md#laws)) exists to
catch the two disagreeing.

## What cannot be migrated

Today's formats are out of scope ([index](index.md#scope-the-system-not-the-history)): they reset at 1.0. Until then,
a store the system can't migrate is never touched by a command on its own. The command that finds it stops and says why;
the user decides, and the only thing that moves it is the user's `comline store reset`, which renames it to a backup.

| Store | Why | What a command does |
|---|---|---|
| A store in a pre-1.0 format with no step to the current one (the unstamped bincode store, formats 1 and 2, older rows of format 3) | Nobody writes those steps. Format 0 is positional: a decode of the wrong layout can succeed and give a different variant, and nothing in the store can check a decode against. | Stops, naming `comline store reset` ([running](running.md#reset)): the store is renamed to `.comline.format-N.bak/`, a new one starts at the next build, `deps-cache/` is kept |
| An unstamped store that decodes as CBOR | The stamp was lost, so the format isn't known. | Stops, unless the user gives one: `comline store migrate --assume-format N`. The decode must succeed for every object |
| A damaged store (a missing or corrupt object, [#182](https://github.com/ComlineProject/core/issues/182)) | A migration needs every object. | Stops, naming the file and how it failed |
| A store newer than the binary | The binary can't read it. | Stops, naming the format and the comline that reads it |

A history can later be rebuilt from Git with `comline store replay` *(proposed; may not be worth building)*. It builds a
**new** history with the current core, one build per release tag or commit the user chooses, never claims to be the old
one, and numbers versions by the current rules.

## Support

| Format | Status |
|---|---|
| 1.0 and later | every format migrates to the next: that is the guarantee this system exists to give |
| 3 (as it stands when the framework ships) | 3→4, the first client: it carries real stores, and exists to prove the system |
| 0 to 2, and older rows of 3 | not migrated; the user resets them (`comline store reset`), and the 1.0 release refuses them |
| test-only formats | in the test tree, never written by a release: [the proof](proof.md#test-only-formats) |

## Where the code lives

**Decided:** a workspace member `comline-ir-formats` (`publish = false` at first) beside `oracle/`, holding one module
per format with its `SCHEMA.md`, types, codec and ledger, and the steps between them. It has no dependency on
`comline-core`, the way the oracle has none, so that a frozen type can't reach for today's. A step `N → N+1` lives
beside the frozen N+1 types. Those exist from the day N+1 is introduced, and are kept equal to the live types by the
`live ≡ frozen(current)` test until N+2 seals them.

Core depends on the crate to read old stores. Test-only formats live in its test tree, not in the shipped modules. The
engine and the CLI commands are in core. The crate's only dependencies are `serde`, `ciborium`, `blake3` and
`lz4_flex`, so the IR-only build, which the `wasm32` consumers use, can carry it: only for in-memory, read-only
migration, never to write a store.

## Decided here

- **New formats use `Known<T>`** for everything they add that a later step might have to leave unknown. The `unknown`
  entry is for retypes that have no room.
- **The `unknown` entry's paths are JSON pointers** into the model: the frozen types already derive serde, and a path then
  reads the same in the format's document and in a test.
- **The `formats` crate also carries the unknown readers and the steps for in-memory, read-only migration in the
  IR-only build (`wasm`),** and never the engine that writes.
