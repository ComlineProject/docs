# Proposal E — adopt an existing model

Status: **under discussion** · Assessed and not recommended as a basis; one
part worth keeping as a feature · See the [section overview](index.md) for the
question all five answer

**The idea:** don't write generators at all. Translate Comline's frozen IR
into an established interface-description model — Smithy, Protocol Buffers,
OpenAPI — and inherit that ecosystem's generators for every language it
already supports.

## Shape

```
comline build  ->  frozen IR  ->  translate  ->  Smithy JSON AST
                                                      |
                                        smithy-typescript, smithy-rs,
                                        smithy-python, smithy-kotlin,
                                        smithy-go, smithy-swift, …
```

Comline keeps the IDL, the parser, the CAS versioning and the diff; one
translator replaces every generator.

**Smithy is the only serious candidate** of the three. Its model is
genuinely close to Comline's: services with operations, structures, unions,
enums, errors as first-class shapes, and an open trait system that could carry
`@deprecated`, `@idempotent` and more. Protocol Buffers has no error-type
concept and a weaker type system; OpenAPI is HTTP-shaped and has no notion of
a protocol in Comline's sense.

## The case for it

- **The leverage is enormous and immediate.** Eight-plus mature, maintained,
  idiomatic generators, written and tested by the people who own each
  ecosystem. No kernel to design, no emitters to write, no per-language
  expertise to acquire. Nothing else in this group comes close on breadth per
  unit of work.
- **Smithy's trait system is a real match** for Comline's annotations, and its
  shape model maps cleanly onto structs, enums, type aliases, protocols and
  errors.
- **It would retire whole categories of this group's problems.** Module
  resolution, imports, naming collisions, manifests, formatting — all of it
  becomes someone else's solved problem.
- **The translation is a small, well-defined artifact** compared with
  maintaining *n* emitters: one mapping, one golden corpus.

## The case against

- **The generators produce the wrong clients.** This is decisive. Smithy's
  generators emit clients for Smithy *protocols* — AWS JSON, REST-JSON,
  RPC v2 CBOR. Comline's wire contract is its own: `IR_HASH` handshake
  agreement, error ordinals on the wire, `@framing` selecting datagram or
  JSON-RPC, and `@comline/runtime` / `comline-runtime` on each end. You would
  inherit excellent *type* generation and then still have to write every
  client, dispatcher and `serve` helper — which is the larger and more
  valuable half of what the current generators do.
- **The toolchain is fatal to current constraints.** Smithy's codegen is
  JVM/Gradle. That ends the single-binary `comline generate`, and it ends the
  wasm playground outright — the one hard constraint in
  [the overview](index.md#one-constraint-narrows-the-field). Comline's own
  compiler would become a schema translator bolted onto a Java build.
- **The mapping is lossy where Comline is distinctive.** `validator` blocks
  with executable `validate` bodies, `settings` blocks and their layering, and
  the CAS-backed per-version generation have no Smithy equivalent. They could
  ride along as custom traits that every inherited generator then ignores —
  so the features Comline is building would be invisible in its output.
- **It inverts ownership of the IDL.** Comline's model would be pinned to
  whatever Smithy can express, and each divergence becomes a translation
  problem. That is a strategic constraint on language design, not just on
  codegen.
- **It is the largest rework of the five** and the hardest to reverse.

## Example projects

| Project | Reused another model? | Outcome |
|---|---|---|
| **Smithy** | n/a — is the model | the comparison point: a JVM codegen framework with a symbol-provider kernel, many targets |
| **ConnectRPC** | yes — protobuf descriptors | successful, because it adopted protobuf's *model and* defined its own protocol on top, writing its own generators |
| **gRPC-Gateway** | yes — protobuf + annotations | works, and shows the cost: behaviour the host generators don't understand has to live in annotations and a custom plugin |
| **Various "OpenAPI → SDK" tools** | yes | broad coverage, and chronically awkward wherever the source model is richer than OpenAPI |

ConnectRPC is the instructive one: it reused the *schema* model and still wrote
its own generators, because the protocol was the point. Comline is in the same
position, with the added difference that it owns its IDL too.

## When this would be the right call

If Comline's value were the IDL and the tooling rather than the wire protocol,
and if a JVM toolchain and the loss of the wasm playground were acceptable.
Neither holds.

**What is worth keeping from this proposal** is the inverse direction, as a
feature rather than a foundation: an **export** from Comline IR to Smithy,
protobuf or OpenAPI, so Comline schemas can be consumed by ecosystems that
already speak those. That is interop — valuable, self-contained, and it
constrains nothing about how Comline's own generators are built.
