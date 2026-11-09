# The catalog

Status: **draft** · part of [A shared vocabulary](index.md)

**The idea:** every name that more than one program needs to agree on is an
entry in one catalog. Code refers to an entry by its id, and each set of names
is a query over the catalog rather than a hand-kept list.

## An entry

```cue
facts: struct_fields: {
    kind:        "fact"
    applies_to:  "format"
    title:       "struct fields"
    description: "How a struct's fields are written: in declaration order, or by name."
    values: {
        by_position: "fields back to back, in declaration order"
        by_name:     "each field keyed by its name"
    }
    proven_by: "vectors"
    since:     "spec-0.6"
    status:    "stable"
}

encodings: "jsonrpc@1": {
    kind:    "framing"
    aliases: ["jsonrpc", "json-rpc"]
    facts: {calls: "by_name", directions: "both", payload: "json"}
    vectors: true
    tags: ["official"]
    status: "stable"
}

guarantees: bounded_size: {
    kind:        "guarantee"
    title:       "bounded size"
    description: "Every value has a maximum size, so a decoder refuses an oversized one before allocating it."
    scopes: ["protocol", "function", "argument", "type"]
}
```

Illustrative, in CUE since the conformance specs already use it. The model is
what matters, not the syntax.

| Field | Meaning |
|---|---|
| **id** | The stable name. For a wire name it is the published spelling and never changes; a rename adds an entry and deprecates the old one. |
| **kind** | `format`, `framing`, `handshake`, `guarantee`, `fact`, `feature`, `annotation`, `setting`, `diagnostic`, `fuzz-target`, `bench`, `report`, and more as needed. |
| **tags** | Free labels that sets are built from: `official`, `nightly`, `1.0`, `no_std`, `experimental`. |
| **title, description** | One source for hover text, docs tables, diagnostics and generated comments. |
| **values** | For a fact or setting, the value domain, each value with its meaning. |
| **aliases** | Other accepted spellings, resolved to the id (`json-rpc` → `jsonrpc@1`). |
| **status, since** | `experimental`, `stable` or `deprecated (use X)`, and the catalog or spec version it arrived in. |
| **relations** | References to other entries: an encoding's facts, the guarantees a handshake establishes, the scopes a guarantee applies at. |

## Kinds worth covering

Every kind where one source would remove copies. In rough order of value:

1. **Encodings, handshakes, their facts and value domains.** These are the
   most duplicated, and the most dangerous to get wrong.
2. **Guarantees.** Core's `Guarantee`, the `accept_unverified` lists, the
   language server's acceptance code, the docs and granular `@unverified`.
3. **Conformance features and report keys.** `features.json`, the spec
   versions, and the Observatory's expected reports.
4. **Annotations and settings keys.** Today unknown ones are silently ignored
   (core#171, core#178). With entries they can be refused, completed in the
   editor and documented from one place.
5. **Diagnostic codes**, with explanations for the CLI and the language
   server.
6. **Fuzz, bench and other CI targets.** The CI matrices, the Observatory's
   `expect:` lists and the READMEs are generated from a set.

## Sets

A set is a query, so it can't drift from the entries (illustrative):

```cue
sets: {
    wire_formats:     [for id, e in encodings if e.kind == "format" {id}]
    nightly_fuzz:     [for id, e in targets if e.kind == "fuzz-target" && list.Contains(e.tags, "nightly") {id}]
    format_facts:     [for id, f in facts if f.applies_to == "format" {id}]
    "spec-0.10":      [for id, f in features if f.since <= "spec-0.10" {id}]
}
```

A consumer asks for a set by name. Generated code exposes the sets that code
needs as constants: a `&[&str]`, an enum, a TypeScript union.

## Relations

**Leaning: plain references.** The catalog could stop at *what exists*, or it
could also state the rules that connect entries:

- a handshake **establishes** guarantees (`comline@1` → schema and encoding agreement);
- an encoding with vectors **keeps** `encoding_conformance`;
- a framing's `payload` must **fit** a format's `output` (the encoding-pair rule);
- `comline@2`'s `same_version_differs = warn` **gives up** `version_honesty`.

Today each of these is code in core (`unverified::causes`, `misfit`), and
some are repeated in the generators. Stating them as data means the compiler,
the conformance engine, the language server and the docs all apply one set of
rules, and a third party's declarations get the same rules. The cost is that
the rule language has to stay small. So the catalog states the relations that
are plain references (establishes, keeps, gives up, applies to, scopes), and
logic that compares values (`fit`) stays in code that reads the catalog.

## Where it lives

**Leaning: a spec repository.** Third parties never edit the catalog: they
declare their own entries (`com.acme.f@1`) in `config.idp`, in the same shape.
What they need from it is what they implement against: the names, the facts
and their domains, and the conformance cases that prove them. That is the
spec, and today its other half, the conformance specs and vectors, sits in
`runtime/conformance`, although a Go or Swift runtime implements against those
and not against the Rust runtime.

So the vocabulary lives in **one spec repository** with:

- the catalog (CUE);
- the conformance specs (`profile.cue`, `features.json`) and vectors, moved out
  of `runtime/conformance`;
- compiler conformance cases (see [granular `@unverified`](granular-unverified.md#testing-the-invariant));
- generated outputs: a `no_std` Rust crate, a TypeScript module, and JSON for
  everything else.

It is versioned as the spec ("spec 0.10" is already how the conformance
corpus is versioned). Everyone, this project's own core, runtime and
generators included, pins the spec the way a third party would. The Rust
conformance engine and reference stay in `runtime`.

The options that were weighed:

| | Spec repository | Vocabulary-only repository | In `core` |
|---|---|---|---|
| What a third party pins | the whole spec: names, facts, vectors and cases | the names, and the vectors separately from `runtime` | a Rust compiler's repository, and every core release |
| Language-neutral | yes: CUE and JSON | yes | no |
| Cost | one more repository, plus moving the conformance corpus | one more repository | lowest |

**Format: CUE as the source.** It is already used for the conformance specs,
it validates (a fact's value must be in its domain), it computes sets, and it
exports JSON. Generated outputs are committed and checked in CI, the same way
`comline.h` is checked against cbindgen.

## How each consumer reads it

| Consumer | Reads | Replaces |
|---|---|---|
| **core** | Generated Rust: guarantees, facts, value domains, official encodings, aliases, annotations, settings keys, diagnostic codes. At build time, a package's own encoding declarations merge in with the same shape. | `Guarantee::name`, `encodings/profile.rs`, `official.rs`'s tables, `official_units.json` |
| **runtime** | Generated Rust constants: `FORMAT_*`, `FRAMING_*`, `HANDSHAKE_*`, the conformance `Fact` names, feature ids. | `contract/names.rs`, `Fact::name`, `features.json` |
| **conformance specs** | The CUE directly. | the fact domains in `profile.cue` |
| **generators** | Generated Rust/TS: names, plus titles for generated docs. | strings in `generation`, comline-rust and comline-typescript |
| **language server** | Generated Rust: completion, hover and quick fixes, deprecations with replacements. | its own lists and acceptance strings |
| **Observatory** | JSON: the expected report keys per set. | `expect:` lists in workflows |
| **CI** | Generated matrices (fuzz targets, bench targets). | hand-kept YAML lists |
| **docs** | Generated tables (encodings, facts, guarantees, features). | hand-kept tables |

## The case for it

- **One edit per change.** Adding a fact value, deprecating an alias or adding
  a fuzz target touches the catalog and nothing else.
- **Unknown names become errors.** Typos in annotations, settings keys and
  acceptances stop passing silently.
- **Tooling for free.** The language server and docs get descriptions and
  deprecations without separate upkeep.
- **Third parties are judged by the same rules,** as with the encoding-pair facts.

## The case against

- **One more thing to version and pin,** in a project where revs already cascade
  across repositories.
- **Generated code in every repository** needs a regeneration check in CI.
- **Rules as data** can grow into a language of its own if relations aren't
  kept to plain references.
