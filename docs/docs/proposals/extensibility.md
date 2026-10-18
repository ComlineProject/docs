# Extending the call system

Status: **under discussion** · tracked in
[core#120](https://github.com/ComlineProject/core/issues/120) · nothing here is
implemented

**The question:** how a developer brings their own wire format, framing,
transport or dispatcher to Comline, and what separates an official extension
from a third-party one.

## Where things stand

The [call system](../guide/runtime/call-system.md) is described as pluggable,
and its runtime half is. The generated half isn't, and nothing connects the two.

| Extension point | Today |
|---|---|
| **Transport** | Open. Anything that moves bytes implements Rust's `Transport` or its TypeScript equivalent. |
| **Wire format** | Open at runtime: `WireFormat` in Rust, `Codec` in TypeScript, picked at the call site. `contract/wire.rs` asks a third-party format to namespace its name (`"com.acme.myformat"`). |
| **Framing** | The runtime trait is open; generated code isn't. A generator bakes the framing into the generated client and server, and knows only `datagram` and `jsonrpc`. Core checks `@framing` against that list, so a third-party framing can't be named in a schema. An unknown `default_framing` silently becomes datagram ([cli#81](https://github.com/ComlineProject/cli/issues/81)). |
| **Dispatcher** | The generated `<Proto>Dispatcher` implements `Dispatch`, and the server is generic over it, so it can be wrapped (for logging, say). That isn't documented. |
| **Generator** | Compiled into the CLI behind cargo features. A third-party language means rebuilding the CLI ([core#8](https://github.com/ComlineProject/core/issues/8); [Proposal D](codegen-architecture/target-language-plugins.md)). |

[Schema compatibility](schema-compatibility.md#encoding-profiles) adds one more
requirement. A format or framing now has a versioned name and a **profile**,
the facts the version comparison reads. A third-party encoding needs both,
and core has to find them somewhere.

## Principles

**Official and third-party encodings use the same mechanism.** "Official" means
maintained in this organisation and shipped by default. It doesn't mean built in
through a path nobody else can use. That's how the standard library already
works: std is a package like any other. If `json@1` is defined the way
`com.acme.cbor@1` would be, the public mechanism is exercised every day and not
only described.

**Only what affects compatibility is declared.** Formats and framings change
what's on the wire, so they're named, versioned, profiled and declared.
Transports and dispatchers don't, so they stay plain runtime code.

## Encodings: formats and framings

### What defines one

An encoding is a **definition**, separate from its implementations:

- **a versioned name:** bare for official encodings (`msgpack@1`), namespaced for
  everyone else (`com.acme.cbor@1`);
- **a profile:** its compatibility facts;
- **vectors:** byte-exact cases in the
  [conformance corpus](https://github.com/ComlineProject/runtime/tree/main/runtime/conformance)
  format, with a vector behind every profile fact.

Implementations, one per language, prove themselves against the vectors, as the
official runtimes do today. The corpus case format and the profile schema
become a **public, versioned spec**. The conformance runner becomes a library a
third party runs in their own CI, against their own vectors.

### How core learns about one

Core knows the official profiles from its pinned copy of the corpus. A
third-party encoding comes **from a dependency**: a Comline package can declare
the encodings it defines in its `config.idp`, for example:

```
encodings = {
    "com.acme.cbor@1" = { kind = "format", profile = "profiles/cbor.json" }
}
```

(The shape is illustrative.) A package that depends on it can use
`com.acme.cbor@1` in its declared formats, and use a declared framing in
`@framing`.

Core can't run another language's code, so it trusts the profile the way it
trusts that dependency's schemas: as declared, and proven in the author's CI.
An encoding named with no profile anywhere is compared under the strictest
profile, with a warning.

### How generated code reaches one

A generator doesn't need to understand a framing to wire it. It needs to know
which type implements that name in its language. That's consumer-side
configuration, like `default_framing` today, so it lives in `comline.toml`, per
target:

```toml
[[generate.target]]
language = "rust"
encodings = { "com.acme.frame@1" = "acme_frame::AcmeFraming" }
```

- The generator emits the mapped type where it would emit `JsonRpcFraming`.
- An encoding that's declared but not mapped for a target is a **generation
  error**, never a fallback.
- The per-package format trait
  ([generation#67](https://github.com/ComlineProject/generation/issues/67)) is
  implemented for each mapped name, so it can't be sealed. A sealed trait would
  shut third-party formats out entirely.

### What a format can't be

A format serializes the data the generated code already produces: the serde
data model in Rust, Shapes in TypeScript. A format that needs more from the
schema, such as field tags or explicit ordinals, isn't a plug-in. It needs
annotations and generator support, and goes through the normal proposal
process as a language feature.

### Becoming official

A third-party encoding becomes official by contributing its profile and vectors
to the corpus and its implementations to the official runtimes. It **keeps its
namespaced name**: renaming it would change the handshake and break every peer
already using it. Bare names are reserved for encodings that start out
official.

## Transports and dispatchers

Neither changes what's on the wire, so neither needs a name, a profile or a
declaration.

- **Transports** stay runtime traits per language. What's missing is a guide:
  the trait, its framing expectations (a message boundary, or a byte stream),
  and how to test one.
- **Dispatchers** are extended by wrapping the generated one. A `Dispatch`
  implementation that delegates to the generated `<Proto>Dispatcher` can log,
  authorise, meter or reject a call before or after it. That should be the
  documented middleware pattern, and the runtime may grow a small helper for
  composing wrappers.

## Generators

Third-party languages are a separate question
([core#8](https://github.com/ComlineProject/core/issues/8),
[Proposal D](codegen-architecture/target-language-plugins.md)). Nothing above
depends on loading generators at runtime. The two meet only when a
third-party language wants a third-party encoding, and the `comline.toml`
mapping already covers that.

## Open questions

- **Trust.** Is "declared by a dependency" enough, or should the dependency
  have to ship vectors as well? Could a tool then check a third-party
  implementation against them?
- **The mapping's default.** Should an encoding's package be able to suggest the
  type that implements it in each language, so the consumer's `comline.toml`
  only overrides it?
- **Shipping implementations.** Could an encoding package carry its crate or npm
  package, so `lib`-mode output depends on it automatically?
- **Transports in the handshake.** Should a transport ever be named, as a
  capability for instance, or stay invisible?

## What it touches

- **runtime:**
  - the public corpus and profile spec;
  - the conformance runner as a library;
  - a transport guide;
  - the dispatcher-wrapping pattern.
- **core:**
  - `config.idp` declarations of defined encodings (building on
    [core#117](https://github.com/ComlineProject/core/issues/117));
  - names declared by dependencies accepted in `@framing` and in declared
    formats.
- **cli:** the per-target mapping in `comline.toml`.
- **generation**, **comline-rust** and **comline-typescript:** mapped types wired
  into generated code; an unmapped encoding is an error.
- **docs:** a guide to writing each extension.
