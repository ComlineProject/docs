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

This is the open question with the most at stake. The catalog could stop at
*what exists*, or it could also state the rules that connect entries:

- a handshake **establishes** guarantees (`comline@1` → schema and encoding agreement);
- an encoding with vectors **keeps** `encoding_conformance`;
- a framing's `payload` must **fit** a format's `output` (the encoding-pair rule);
- `comline@2`'s `same_version_differs = warn` **gives up** `version_honesty`.

Today each of these is code in core (`unverified::causes`, `misfit`), and
some are repeated in the generators. Stating them as data means the compiler,
the conformance engine, the language server and the docs all apply one set of
rules, and a third party's declarations get the same rules. The cost is that
the rule language has to stay small. **Suggested:** state the relations that are
plain references (establishes, keeps, gives up, applies to), and keep logic
that compares values (`fit`) in code that reads the catalog.

## Where it lives

Undecided. The options:

| | A. Its own repository (`comline-vocabulary`) | B. In `core` | C. In `docs` |
|---|---|---|---|
| Who depends on it | everyone, and it depends on nothing | everyone already pins core | nobody pins docs today |
| Fits the dependency order | yes: it sits below core, runtime and the generators | runtime and generators already depend on core, so no new edges, but runtime would pin core for names alone | it would need a published artifact |
| Third-party view | clearly the vocabulary, not one program's | reads as core's internals | reads as documentation |
| Cost | one more repository, rev and CI | lowest | low, but odd for code to depend on |

**Suggested: A**, a small repository holding the CUE sources and the
generated outputs (a `no_std` Rust crate, a TypeScript module, JSON for
anything else), versioned on its own. Everything pins it the way the
generators pin core today. B is the fallback if one more repository isn't
worth it yet.

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
