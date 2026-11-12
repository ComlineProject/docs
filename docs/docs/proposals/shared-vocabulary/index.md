# A shared vocabulary

Status: **accepted** · decided 2026-11-12 · tracked in [core#219](https://github.com/ComlineProject/core/issues/219), [core#220](https://github.com/ComlineProject/core/issues/220)
and [core#222](https://github.com/ComlineProject/core/issues/222) · two parts, read in order:
[the catalog](catalog.md), then [granular `@unverified`](granular-unverified.md)

**The question.** Comline names many things that several programs have to
agree on: encodings, handshakes, guarantees, facts and their values,
conformance features, annotations, settings keys, diagnostic codes, and fuzz,
bench and report targets. Every repository that needs a name writes it out
as a string and keeps its own list of the sets it belongs to. **Can those names,
and the sets made from them, be defined once and shared by core, the compiler,
the runtimes, the generators, the language server, the Observatory and the
docs?**

A second question depends on the first. `@unverified` marks a protocol as
giving up guarantees, but the author can't say *which* ones, give each its
own reason, or mark less than a whole protocol. Once guarantees are entries in
a shared vocabulary, a marker can refer to them.

## What it looks like today

A name is a literal, copied wherever it's needed:

| Name | Kind | Written in |
|---|---|---|
| `packed@1`, `comline@2` | encoding, handshake | runtime (~46 files), core (~20), docs (~40), language server |
| `framing-datagram` | conformance feature | runtime, core, comline-typescript, docs |
| `struct_fields`, `unknown_variant` | fact | core's `encodings/profile.rs`, runtime's conformance `profile.rs` (an enum and a hand-written `match` to strings), the conformance CUE specs, docs |
| `schema_agreement`, `bounded_size` | guarantee | core's `Guarantee` (an enum and a `match`), `config.idp` acceptances, the language server, docs |
| `packed_canonical` | fuzz target | the fuzz `Cargo.toml`, two lists in `fuzz.yml`, the fuzz README, the seed generator |

Sets are kept by hand too. *Which fuzz targets exist*, *which features a spec
version covers*, *which values `calls` can take* and *which names are wire
formats* each live in a CI matrix, a JSON file, a `match` arm or a completion
list. Adding or renaming a name means finding every copy, and nothing checks
that the copies agree.

Some of the structure already exists. The conformance specs' `profile.cue`
gives each fact its value domain and how it is proven. Core's
`encodings/profile.rs` lists the same facts again, and resolves aliases
(`jsonrpc`, `json-rpc`) in `official.rs`.

## What this proposes

1. **[A catalog](catalog.md):** every shared name becomes an entry with a
   stable id, a kind, tags, metadata and, where it applies, a value domain,
   aliases, a status and relations to other entries. Sets are queries over
   kinds and tags. Each consumer reads the catalog, or code generated from it,
   instead of keeping its own copy. Official entries and a package's own
   declarations (`com.acme.f@1`) have the same shape.
2. **[Granular `@unverified`](granular-unverified.md):** the marker may name
   the guarantees it covers, each with its own reason, and may apply at the
   scope a guarantee naturally has (a protocol, a function, an argument).
   Core keeps working out what is given up, and checks it against what the
   author wrote. This revisits part of the
   [guarantee-marker decision](../guarantee-marker/index.md); that page's
   last open question asks for exactly this fixed vocabulary of guarantees.

## Rules that hold whatever the details

- **A published wire name never changes.** `packed@1` and `comline@2` are hashed
  into the handshake, so their spelling is protocol. A rename is a new entry,
  with the old one deprecated.
- **Third parties are first-class.** Anything the catalog can say about an
  official encoding, a package can say about its own, and the same rules
  judge both (as for the encoding-pair facts).
- **Nothing new at run time.** The catalog feeds compilers, generators,
  tooling and CI. Runtimes keep compile-time constants, with no lookup on the
  call path.
- **One change, every consumer.** Adding a name, a value or a set member is an
  edit to the catalog plus regeneration. Hand-kept copies are a bug.

## Rollout

In stages, each useful on its own, in the order the encoding-facts work used:

1. **The spec repository** ([catalog → where it lives](catalog.md#where-it-lives)):
   the catalog in CUE, seeded from `profile.cue`, core's `Guarantee` and the
   official encodings, with the conformance specs and vectors moved in from
   `runtime/conformance`. *Done.*
2. **Core reads it:** guarantees, facts, value domains, aliases and official
   encodings come from the catalog. Unknown annotation names, settings keys
   and diagnostic codes are refused (core#171, core#178). *Done for guarantees,
   facts, aliases and encodings. The refusal waits until the catalog holds
   annotations, settings keys and diagnostic codes.*
3. **The runtime and conformance read it:** fact names, conformance
   features, and the fuzz and bench target sets. The CI matrices and the
   Observatory's expected reports are generated from it. *Done for the fact
   names, the features and the fuzz targets.*
4. **Granular `@unverified`** in core: grammar, scopes, per-package
   acknowledgement pinned to each cause's chain, and freezing. It needs
   keyed annotation values (core#124). It lands with its safety tests: a
   property test against an oracle, a fuzz target, compiler conformance cases
   in the spec repository, and an audit of every path that judges guarantees.
5. **Tooling reads it:** language server completion and hover, generated
   `@unverified` docs (generation#93), and the docs tables.

## What was decided

- **Home:** a spec repository, `ComlineProject/specification`, holding the
  catalog, the conformance specs and vectors, and compiler conformance cases,
  versioned as the spec. A vocabulary-only repository and `core` were
  rejected.
- **Format:** CUE as the source, with generated outputs: the `comline-catalog`
  Rust crate and `catalog/gen/catalog.json`.
- **Relations:** plain references only (establishes, keeps, gives up, applies
  to, scopes); logic that compares values stays in code. Going further is
  [open](#still-open).
- **`@unverified`:** plain or keyed, at the scopes each guarantee states in
  the catalog. Outer covers inner, with `annotations.unverified.strict = true`
  as the opt-in to the keyed form at the innermost scope. Acknowledged once
  per package along a chain, never inherited, pinned to the chain, accepted
  per protocol, failing closed.
- **Package defaults:** acknowledged in `config.idp` next to the setting that
  causes the loss, covering only that cause.
- **Spec upgrades:** a loss found by a newer spec asks the author and consumers
  again, and `diff` recomputes both versions under it, so it is never a false
  major change.
- **Versions:** the spec version and the IR format version are independent,
  with each frozen version recording its spec version, and the spec
  append-only for anything frozen. Granular `@unverified` changes the frozen
  shape (scopes, chains), so it is IR format 4.
- **The word:** `@unverified` for both forms.

## Still open

- **How far relations go beyond plain references.** The catalog states
  establishes, keeps, gives up, applies to and scopes. Whether it ever states
  rules that compare values (`fit`) is not decided; those stay in code.

Not open, but not built yet: keyed annotation values (core#124), the
annotation, settings-key and diagnostic-code kinds in the catalog, and
granular `@unverified` itself with its safety tests (core#222 to core#225).
