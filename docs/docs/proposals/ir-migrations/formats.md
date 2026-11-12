# The formats

Status: **draft** · part of [Migrating stored IR across format versions](index.md)

**The question.** What exactly is in a store, which of it depends on the IR format, and what does a format
number promise about it?

## What a store holds

| Path | Holds | Depends on the format |
|---|---|---|
| `objects/<xx>/<rest>` | One object: LZ4 over CBOR, addressed by the blake3 of the CBOR. Three kinds: `Blob { content }`, `Tree { entries: [{ mode, name, hash }] }`, `Commit { tree, parents, author, timestamp, message, version, release? }`. | The *container* does not. See below. |
| a blob's `content` | One frozen schema unit (`FrozenUnit`), or a version's `config` (a list of config units), `docs`, `facts` (`History`), a dependency's `manifest`, `config` and `dependency_configs`. | **Yes.** This is what a format version describes. |
| `refs/heads/main` | The hash of the newest commit, hex. After a Git merge, conflict markers around two. | No |
| `FORMAT_VERSION` | The stamp. | It is the stamp. |
| `deps-cache/` | Git checkouts of dependencies. A cache, ignored by Git. | No, and not part of the store |

A version's root tree has one `schema_<n>` tree per schema file, a `dep_<name>` tree per vendored dependency
(`schema_<n>`, `manifest`, `config`, `dependency_configs`), and the blobs `config`, `docs` and `facts`. The
[CAS guide](../../guides/ir/cas.md) describes this for format 3.

**Proposed: the container is not a format.** The object layout (CBOR, LZ4, blake3, `Blob`, `Tree`, `Commit`, the
ref file) is the same in formats 1 to 3, and a format version covers the payloads inside it. Three things follow:

- A reader of the container needs no format knowledge. The CLI and core can list versions, read each commit's
  `version` and `release`, and walk parents in any store they can find the container of. Today
  `resolved_version` reads a dependency's committed `.comline/` this way and falls back to `0.0.0-unbuilt` on any
  failure, which hides a store it merely couldn't read.
- A change to the container (the hash, the compression, the ref layout) is also a format change, and a step like
  any other. Its model is the whole store.
- Every hash above a changed payload changes with it, because parents, tree entries and `release.since` are all
  hashes. See [hashes](hashes-and-history.md#object-hashes).

## History of the formats

| Format | Stamp | On `master` | What it is |
|---|---|---|---|
| **0** | none | 2026-01-10 (`534da82`, the CAS), config blob 2026-08-30, dependencies vendored 2026-09-30, until 2026-10-11 | bincode, which tags struct fields and enum variants by position, no names on the wire. About 20 commits reshaped the persisted types in this period, none of them marked. |
| **1** | `1` | 2026-10-11 (`f71ef96`, PR #84) | Name-tagged CBOR. `ensure_compatible_store` and the stamp are introduced. `FrozenUnit::Parameter` removed. |
| **2** | `2` | 2026-10-12 (`dbdb13f`, PR #87) | `Property`'s `expression: Option<String>`, the written value with its quotes stripped, becomes `value: ConfigValue`, which keeps the written form. A field renamed and retyped. |
| **3** | `3` | 2026-10-18 (`eda0684`, PR #108) | Types stop being `KindValue` text: `TypeRef` (`Primitive`, `Named`, `Array { element, length }`, `Union`, `Unit`), `Literal` and `Condition`. `Field`/`Constant` `kind_value` becomes `ty` and a literal; `EnumVariant` holds its name; `Assert` gains `expr`. |

Notes that matter to migration:

- **Format 1 lived about 15 hours on `master`.** Core's CI was green at its first merge (`d2763cd`, 2026-10-11) and at
  format 2's (`59587ba`, 2026-10-12). No CLI revision pinned core in format 1.
- **Format 2's lossiness is real.** `KindValue` text froze `T[8]` and `T[]` both as `T[]`, and `f32` and `f64` both
  as `float`. A 2→3 step cannot recover either. Format 1's `expression` had no quotes: `@framing = "datagram"` and
  `@framing = datagram` read the same, so a 1→2 step cannot say which form was written.
- **The CLI pinned format 0 until 2026-10-11 (`f934a66`, core `f035379`), format 2 from 2026-10-12 (`086cd32`) to
  2026-10-18 (`00ee242`), and format 3 from 2026-10-18 (`1455192`).** Those revisions have a committed
  `Cargo.lock`, and the git revisions their `Cargo.toml` names (core, generation, comline-rust, comline-typescript)
  all still exist. [The proof](proof.md#building-the-old-revs) uses
  them.

## Format 3 is a family

The doc comment on `CURRENT_IR_FORMAT_VERSION` says growing `FrozenUnit` needs no bump. Since 2026-10-18 these have
been added without one, and so a "format 3" store can lack any of them:

| Added | Commit | Absent reads as |
|---|---|---|
| validator call `span`, `arg_spans` | `0983015`, 10-18 | unknown span, `(0, 0)` |
| type alias `parameters` | `8243d98`, 10-18 | none |
| `Assert.message_span`, `uninterpolated`; validator `validate_span` | `ad2b3f5`, 10-19 | none |
| `Unverified(Vec<Guarantee>)` in a protocol's parameters; the `Guarantee` enum | `bd9d9f4`, 10-20 | no recorded set |
| `Commit.release` | `af0371f`, 10-20 | a release only if the version has no pre-release part |
| config units `Handshake`, `HandshakeParams` | `6571780`, 10-20 | the default handshake **of the reading core** |
| config unit `Wire` | `031d74c`, 10-25 | the default format and framing **of the reading core** |
| `ConfigValue::Dict` | `a5d6f85`, 10-25 | a variant older readers can't decode |
| config unit `Encoding` | `f643d51`, 10-31 | no declaration |
| root `docs` blob | `038591e`, 11-01 | no `//!` headers |
| root `facts` blob; config unit `PackageId` | `f873d98`, 11-01 | computed when read; no id |
| `Encoding.establishes`, `has_vectors` | `4ba7c57`, 11-01 | the strict reading: nothing established, no vectors |
| `PrimitiveType::Char`, `Array.max` | `4eb6228`, 11-02 | a variant older readers can't decode; no maximum |
| `Guarantee::BoundedSize` | `2b6d636`, 11-02 | a variant older readers can't decode |
| facts' `number`, `retired`, `numbered` | `8ec27df`, 11-03 | `numbered = false`: computed when read |
| `Encoding.grammar`, `calls`, `directions` | `4da05ab`, 11-07 | none |
| facts' per-protocol `encodings`; the defaults moved to `datagram@3` and `comline@2` | `bbbd957`, `9a6482e`, 11-08 | resolved when read, with what an absent value *was* (`IMPLICIT_FRAMING`, `IMPLICIT_HANDSHAKE`) |
| config unit `Unverified` | `9ea142e`, 11-10 | none |
| `dep_<name>/config`, `dependency_configs` | `965e781`, 11-12 | **unseen**: not empty, not defaulted |
| `FrozenArgument.parameters` (markers on arguments) | `66feecb`, 11-12 | none |

The rule, as written, is sound for the direction it was written for: a new core reads an old store. It has four
gaps, and a migration framework has to close them:

1. **A store holds commits of several ledger levels.** Each build writes what its core knew. The absent-entry
   reading is per commit and per entry, so "format 3" says nothing about which of the rows above a given version
   has.
2. **The rule is one-directional.** A shipped binary that meets a new *variant* (`BoundedSize`, `Dict`, `Char`) fails
   to decode. One that meets a new *field* drops it without a word. Neither is checked.
3. **Some additions change what old bytes mean.** An old version's `Unverified(Vec<Guarantee>)` has no
   `bounded_size`, because the guarantee didn't exist; under today's spec the same schema gives it up. An absent
   `wire.framing` meant `datagram@2` when it was built and `datagram@3` now, so a reader has to say which.
4. **Nothing checks it.** `f71ef96` records the decision not to add a golden-hash check, "can revisit if it becomes a
   real recurring problem". Twenty additions in 25 days is that.

## Each format is written down

**Proposed:** a format is not "whatever the types were at that commit". Each format N has a directory in a new
`formats` crate, and these four things in it:

| File | Holds |
|---|---|
| `SCHEMA.md` | Every blob, tree and entry; every field, its type and meaning; what an absent entry or field means (the *absence reading*); the ledger. The source of truth for the format. |
| `types.rs` | Frozen copies of the format's types: serde derives and nothing else, with no behaviour, no dependency on `comline-core`, and every `#[serde(...)]` attribute that decides the bytes. |
| `codec.rs` | `decode` and `encode` between bytes and the format's model. The only code that touches format-N bytes. |
| `ledger.toml` | One row per addition made without a bump: the commit, the date, what was added, the absence reading, and the fixture that has it. |

A format is **sealed** when the next one is introduced: `formats/MANIFEST` records the blake3 of each sealed
directory, and CI fails if one changes. The current format is not sealed, and it is held to the live types by a
test instead: `live ≡ frozen(current)`, meaning that for every fixture and for random values, the core's types and
the frozen copy encode to the same bytes and decode each other's. A change to the live types without the same
change in the frozen copy fails it, and so does a change that alters a fixture's bytes.

This replaces the doc comment's rule with a checked one. Without a bump, the only changes allowed are:

- a new entry in a root or dependency tree whose absence reads as unknown;
- a new field with `#[serde(default)]` and `skip_serializing_if` for the default, so that content which doesn't use
  it keeps its bytes;
- a new enum variant, if nothing existing needs it.

Each one adds a ledger row and the same lines to the frozen copy, in the same pull request. Any other change is a
bump. The `skip_serializing_if` condition is the one the code already follows ("so a schema without bounds freezes
to the same bytes as before them"), because the bytes of a frozen unit are also what a [dependency pin
hashes](hashes-and-history.md#pins).

## Still open here

- **Whether `SCHEMA.md` is the source and the [CAS guide](../../guides/ir/cas.md) links to it, or the guide stays the
  description of the current format and `SCHEMA.md` is generated beside it.** Leaning: `SCHEMA.md` in core is the
  source; the guide describes the current format and says so.
- **Whether an additive change should raise a second number** (a ledger level, beside the format) so that an older
  binary refuses to *write* into a store whose commits use additions it would drop. This would turn gap 2 into an
  error. The cost is a second stamp to keep in step.
