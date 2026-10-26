# Proposals

Ideas for the project from authors and contributors, triaged for fit. A proposal
captures a direction and its trade-offs. Once the team commits to one, the
rationale and rollout move to a [Design](../design/index.md) record and the
proposal is marked **accepted**.

## How a proposal is written

Each page opens with a `Status:` line, house style — a status in bold followed by
` · `-separated notes:

- **draft** — being written, not yet up for discussion
- **under discussion** — open for feedback
- **accepted** — the team is going this way; see the linked Design record
- **implemented** — accepted and shipped; the page says where what shipped
  differs from what it proposed
- **rejected** / **superseded** — with a note saying why, and by what

Proposals may **compete**: two pages proposing different answers to the same
question. They are grouped together below and stay open until one is accepted;
the others become rejected or superseded with a one-line reason.

## By area

### [Runtime & codegen repository organization](repo-organization/index.md)

How the per-language surface — codegen, libgen, runtime — is split across
repositories. Two competing proposals, read to the same shape:

- [Proposal B — split by language](repo-organization/split-by-language.md) — one
  repo per target holds that language's codegen, libgen, and runtime together.
  ***accepted*** — adopted directly by the design record.
- [Proposal A — split by concern](repo-organization/split-by-concern.md) —
  `generation` stays one repo; `runtime` graduates heavyweight language runtimes
  to their own repos. *rejected — superseded by B; kept for the reasoning.*

Org-wide decision record:
[Design → Runtime & generation repository structure](../design/runtime-repo-structure.md).

### [How generators are built](codegen-architecture/index.md)

Whether generation stays hand-written Rust that pushes strings, and what the
alternatives are worth. Five proposals, read to the same shape:

- [Proposal A — a shared resolution kernel](codegen-architecture/resolution-kernel.md)
  — a symbol/module layer in `comline-codegen`; generators map a resolved
  model to syntax. *under discussion — the recommendation of the group.*
- [Proposal B — templates](codegen-architecture/template-rendering.md) —
  per-language template files replace `push_str`. *under discussion —
  complementary to A, not a substitute.*
- [Proposal C — syntax trees](codegen-architecture/syntax-tree-emission.md) —
  build an AST per target and pretty-print it. *under discussion — one cheap
  component recommended, the whole not.*
- [Proposal D — target-language plugins](codegen-architecture/target-language-plugins.md)
  — `protoc`-style: each generator is a program in its own language. *under
  discussion — blocked by the wasm playground, not rejected.*
- [Proposal E — adopt an existing model](codegen-architecture/adopt-existing-model.md)
  — translate Comline IR to Smithy and inherit its generators. *under
  discussion — assessed, not recommended as a basis.*

### [Shared runtime core](shared-runtime-core/index.md)

How ten or more language runtimes stay correct, conformant and fast without
writing the same logic in each. One Rust protocol core every language binds,
codecs generated from one plan, and every language proven against the Rust
reference. One proposal in three stages, read in order:

- [Stage 1 — verification](shared-runtime-core/verification.md): differential
  fuzzing against the Rust reference, and benchmark gates, in every
  language's CI. ***accepted***, stage 1 in progress: the reference process,
  fuzz targets and benchmark gates are built for Rust.
- [Stage 2 — core interface](shared-runtime-core/core-interface.md): the
  handshake, framings and connection state machine behind a stable C ABI and
  WASM, built from one crate. ***accepted***, steps 1–3 built: the core
  changes, the C ABI at 0.1 ([reference](../reference/c-abi.md)), and its
  vectors, fuzzing and benchmarks. Bindings and ABI 1.0 are next.
- [Stage 3 — generated codecs](shared-runtime-core/generated-codecs.md):
  native per-type codecs and protocol glue rendered from one plan in the
  codegen kernel. *under discussion.*

### Versioning

- [Schema compatibility](schema-compatibility.md): which schema changes are
  breaking, measured by the wire and by the names consumers use, with formats
  and framings versioned and declared by the package so the rules can depend
  on them. *under discussion.*
- [Language target versions](target-versions.md): what the version in
  `rust#1.70.0` means, how it picks a generator, and how feature support and
  output depend on it, proven by conformance at each version where they
  change. ***implemented***.

### Extensibility

- [Extending the call system](extensibility.md): how developers bring their own
  wire formats, framings, transports and dispatchers, with official encodings
  defined through the same public mechanism as third-party ones. *under
  discussion.*

#### [Marking a given-up guarantee](guarantee-marker/index.md)

How a schema marks an extension that gives up one of Comline's guarantees
between peers, the role `unsafe` plays in Rust. Four competing proposals, read
to the same shape:

- [Proposal C — `@unverified`, one marker](guarantee-marker/unverified.md):
  core infers which guarantees are affected. ***accepted***, with the
  consumer's acceptance recording that set.
- [Proposal A — `@waives`, per guarantee](guarantee-marker/waives.md): names
  each guarantee given up. *rejected: repeats what core computes.*
- [Proposal B — `@assumes`, per guarantee](guarantee-marker/assumes.md): names
  what the author assumes holds instead. *rejected: same, and its direction can
  be misread.*
- [Proposal D — keep `@unchecked`](guarantee-marker/unchecked.md): the original
  name. *rejected: says neither who nor what.*

### Connections

- [Connections](connections.md): what a connection carries beyond one client
  calling one server: calls in both directions on a transport-independent core,
  per-connection state and interceptors, several protocols per connection.
  *accepted; calls both ways and several protocols built.*
- [Package wire defaults](package-wire-defaults.md): a `wire` key in
  `config.idp` for the package's framing and format, `datagram@2` as the
  built-in framing, a new packed C-struct-like format `packed@1` as the
  built-in format, and a generated `Services` struct with a package-level
  `serve`. *shipped.*

### Packet protocols

- [Packet dispatch](packet-dispatch.md): message-oriented packet protocols
  (families, explicit ids, phases, `@provider` for direction), with addressing
  in the schema, generated dispatch tables, and an official configurable
  framing. *under discussion, partly decided.*

#### [Function ids](function-ids/index.md)

How an explicit function id is written. Two competing proposals:

- [Proposal A — an `@id` annotation](function-ids/annotation.md).
  ***accepted***, with assignment on build and a reuse guard.
- [Proposal B — a prefix on the declaration](function-ids/prefix.md), from the
  2024 proposal. *rejected.*

#### [Phase syntax](phase-syntax/index.md)

How phases are written. Two competing proposals:

- [Proposal A — an enum plus annotations](phase-syntax/enum-and-annotations.md):
  phases are an ordinary enum; `@phase` and `@transition` on the declarations.
  ***accepted.***
- [Proposal B — a `phase` block](phase-syntax/phase-block.md): a new
  declaration lists each phase in one place. *rejected: a new construct and a
  second table.*

#### [Tagged unions](tagged-unions/index.md)

Whether "one of several shapes, with a tag" is a feature of `enum` or of
`union`. Three competing proposals, *under discussion*:

- [Proposal A — a `union` declaration](tagged-unions/union-declaration.md):
  members written like struct fields, tagged with `@id`. *leaning.*
- [Proposal B — enum variants that carry data](tagged-unions/enum-variants.md),
  as in Rust and Swift.
- [Proposal C — both](tagged-unions/both.md).

### Tooling

- [Automatic documentation](auto-documentation.md) — an optional tool that
  documents a user's own schemas and packages — their structs, enums, protocols,
  errors — from the IR and its docstrings, with the CAS supplying per-version
  docs and a generated changelog. *draft.*
