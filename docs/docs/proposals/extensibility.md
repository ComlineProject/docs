# Extending the call system

Status: **implemented** · tracked in
[core#120](https://github.com/ComlineProject/core/issues/120) (with
[core#121](https://github.com/ComlineProject/core/issues/121) and
[runtime#18](https://github.com/ComlineProject/runtime/issues/18)) · see
[What shipped](#what-shipped) for the pull requests and for where it differs
from the text below, which is kept as decided. The user guide is
[Extending Comline](../guide/extending/index.md).

The open questions were decided on 2026-10-31.

**The question:** how a developer brings their own wire format, framing,
handshake, transport or dispatcher to Comline, what separates an official
extension from a third-party one, and how an extension that gives up Comline's
guarantees is made visible.

## Where things stood

This is the position before the work; [What shipped](#what-shipped) says what
changed.

The [call system](../guide/runtime/call-system.md) is described as pluggable,
and its runtime half is. The generated half isn't, and nothing connects the two.

| Extension point | Today |
|---|---|
| **Transport** | Open. Anything that moves bytes implements Rust's `Transport` or its TypeScript equivalent. |
| **Wire format** | Open at runtime: `WireFormat` in Rust, `Codec` in TypeScript, picked at the call site. `contract/wire.rs` asks a third-party format to namespace its name (`"com.acme.myformat"`). |
| **Framing** | The runtime trait is open; generated code isn't. A generator bakes the framing into the generated client and server, and knows only `datagram` and `jsonrpc`. Core checks `@framing` against that list, so a third-party framing can't be named in a schema. An unknown `default_framing` silently becomes datagram ([cli#81](https://github.com/ComlineProject/cli/issues/81)). |
| **Handshake** | **Built** ([runtime#18](https://github.com/ComlineProject/runtime/issues/18)): a declared axis. `comline@1` or `none`, from `@handshake`, the package's `handshake`, or the default; a runtime trait with `connect_with` / `serve_with`; skip paths named `*_unverified`. Custom names wait on third-party encodings. |
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

**Only what affects compatibility is declared.** Formats, framings and
handshakes change what's on the wire, so they're named, versioned, profiled and
declared. Transports and dispatchers don't, so they stay plain runtime code.

**Guarantees can be given up, but never quietly.** Comline talking to Comline
keeps every guarantee by default. Giving one up, to talk to a legacy system say,
is allowed. It takes an explicit, reasoned marker, it's off unless a package
turns it on, and every consumer sees it and accepts it in writing. That's the
role `unsafe` plays in Rust; see [Giving up a guarantee](#giving-up-a-guarantee).

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
trusts that dependency's schemas: as declared. Whether the profile is proven
depends on the vectors behind it (see [Test vectors and trust](#test-vectors-and-trust)).
An encoding named with no profile anywhere is compared under the strictest
profile, with a warning.

### Test vectors and trust

Decided 2026-10-20 ([core#120](https://github.com/ComlineProject/core/issues/120)):

| Kind | Requirement | Result |
|---|---|---|
| **Official** | Vectors for every fact in its profile, implementations for every official target, conformance passing in CI, and a spec page: everything Comline requires | Fully trusted |
| **Third-party, with vectors** | Vectors shipped by its package, and a check (say `comline conformance`) that runs an implementation against them | Conformance proven; nothing given up |
| **Third-party, without vectors** | None | Encoding conformance is [given up](#giving-up-a-guarantee): `@unverified` with a reason, and the consumer's acceptance |

Nothing forces a third-party author to write vectors, but skipping them is
visible to every consumer.

### How generated code reaches one

A generator doesn't need to understand a framing to wire it. It needs to know
which type implements that name in its language. That's consumer-side
configuration, so it lives in `comline.toml`, per target. Which encoding a
protocol uses is the producer's choice, made in the schema and its
`config.idp`; only *how* it's implemented in each language is the consumer's:

```toml
[[generate.target]]
language = "rust"
encodings = { "com.acme.frame@1" = "acme_frame::AcmeFraming" }
```

- **The encoding's package can suggest a default mapping** per language (in
  Rust `acme_frame::AcmeFraming`, in TypeScript `@acme/frame`), so a consumer
  writes nothing unless it wants something else (decided 2026-10-20).
- **The suggested mapping also names the implementation's package and
  version** (a crate or an npm package). Decided 2026-10-31:
  - Generated `lib` output adds that dependency automatically.
  - A consumer can still override it in `comline.toml`.
  - It relies on the hosted registry, which ships at 1.0 (see
    [Ready for 1.0](../conduct/readiness.md)).
- The generator emits the mapped type where it would emit `JsonRpcFraming`.
- An encoding that's declared but neither mapped nor suggested for a target is
  a **generation error**, never a fallback.
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

## Handshakes

Comline's handshake guarantees that both ends were built from the same schema
and agree on format and framing. That's right for Comline talking to Comline. An
implementer fronting a legacy system may need that system's own hello, version
negotiation or authentication exchange, or no handshake at all, knowing they
give up those guarantees. So the handshake is a declared axis like the other
two:

- **Versioned names:** `comline@1` is today's frame, `none` is an official
  choice, and a custom handshake is namespaced (`com.acme.legacy-hello@1`). A
  handshake that checks compatibility instead of exact identity
  ([runtime#15](https://github.com/ComlineProject/runtime/issues/15)) becomes
  `comline@2`, a new version, not a change forced on everyone.
- **Chosen by the producer,** with the same layering as framings: the
  protocol's `@handshake`, then the package default in `config.idp`, then
  core's default `comline@1`. Talking to a legacy system is a property of the protocol,
  not of one call site. A skip decided at a call site can leave one peer
  handshaking and the other not, with nothing in the schema showing it.
- **Its profile states what it establishes,** not how it's encoded: schema
  agreement, encoding agreement, both or neither. A custom handshake isn't
  weaker or stronger than Comline's; it may well do more, authentication for
  instance. What matters is whether it establishes the guarantees Comline
  relies on. If it doesn't, the protocol
  [gives those guarantees up](#giving-up-a-guarantee).
- **Implemented like any encoding.** In the runtimes, `Handshake` becomes a trait
  that receives the transport plus what generated code knows (IR hash, package
  version, format and framing names) and decides what to send and check. A
  custom one is mapped to a type per target in `comline.toml`
  ([runtime#18](https://github.com/ComlineProject/runtime/issues/18)).

Comline can then also describe a protocol it doesn't own, with a custom framing,
handshake and perhaps format. The guarantees Comline can't give are the
implementer's, and say so.

### Checking compatibility: strategies and `comline@2`

Decided with the user (2026-10-20), for
[runtime#15](https://github.com/ComlineProject/runtime/issues/15).
`comline@1` compares a hash of the whole frozen schema, so any edit, even a
docstring, makes peers refuse each other, and the refusal carries no reason.

How systems answer "can these two talk?" differs, and **each of these should be
achievable as a handshake,** even where it isn't what `comline@2` does:

| Approach | Used by |
|---|---|
| **One exact version number** | Minecraft (protocol version) |
| **Exchange versions, then use the lower one** | Bitcoin (`version` message); SSH and TLS pick from lists |
| **A version range per API** | Kafka `ApiVersions`: min and max per request type, the highest common one wins |
| **Send the schema and resolve the differences** | Avro (writer and reader schema, or a registry fingerprint) |
| **No handshake; tolerance rules only** | Protobuf, Thrift, Cap'n Proto |

#### Core provides the facts; the handshake picks the strategy

Core computes compatibility facts from the package's history, and generated
code embeds them. Every strategy works from the same set:

| Fact | Exact (Minecraft) | Lower version (Bitcoin) | Per-API ranges (Kafka) | Schema exchange (Avro) | `comline@2` |
|---|---|---|---|---|---|
| package identity (a stored id, see below) | ✓ | ✓ | ✓ | ✓ | ✓ |
| package version | ✓ | ✓ | | | ✓ |
| per-protocol **line**: the version it last broke at | | | ✓ | | ✓ |
| per-protocol wire-shape hash | ✓ (in place of the version) | | | ✓ (as a fingerprint) | ✓ |
| per-function "since" version | | | ✓ | | ✓ |
| encoding name and parameter hash | ✓ | ✓ | ✓ | ✓ | ✓ |
| the wire shape itself, as a compact description | | | | ✓ | |

- **A handshake's profile lists the facts it needs,** and generated code
  embeds only those. The wire shape itself is emitted only for a handshake
  that asks for it.
- **A custom handshake** (`com.acme.…@1`) reads them through the same
  `Handshake` trait as `comline@2`.
- **The wire-shape hash** covers only what reaches the wire, with aliases
  resolved. It leaves out docstrings, spans, validators, constants, advisory
  annotations and the namespace, and it includes the encoding's parameters.
- **Package identity** is an id stored once in `config.idp`, not the package
  name, so renaming a package doesn't break its peers, as function ids survive
  function renames.

#### `comline@2` and its parameters

What decides a connection under `comline@2`:

- **The line decides, and the shape hash is sent as well.** For 1.0 and up
  the line follows the major version; before 1.0 it follows the minor, as
  Cargo's `0.x` convention does.
- **The rest is situational, so it's a parameter of the handshake,**
  declared in `config.idp` like [framing instances](packet-dispatch.md#where-the-framings-parameters-are-written).
  The defaults are shown:

  ```
  handshakes = {
      "default" = {
          handshake = "comline@2"
          scope = "protocol"               # or "package"
          newer_consumer = "degrade"       # or "refuse"
          same_version_differs = "refuse"  # or "warn"
          exchange = "offer"               # or "symmetric"
      }
  }
  ```

  A package with one handshake never writes this; plain `"comline@2"` means the
  defaults.

| Parameter | Values | Meaning |
|---|---|---|
| `scope` | `protocol` (default), `package` | Compare each protocol's line, so a break in one protocol doesn't stop peers using only another; or compare the package's |
| `newer_consumer` | `degrade` (default), `refuse` | A consumer newer than its provider either connects, knowing the peer's version, so a call to a function the peer lacks fails locally with a clear "peer is on 1.2" error and is never sent; or is refused |
| `same_version_differs` | `refuse` (default), `warn` | Two builds claiming one version with different shapes, typically two branches that each added a function, are refused with a reason naming both; or only warned about |
| `exchange` | `offer` (default), `symmetric` | The client offers per protocol (its id, line, version and shape hash) and the server answers each with accepted plus its own version, or refused plus a reason; or both sides send the same frame and check independently |

- **Wire parameters and policy parameters.**
  - `exchange` changes the bytes exchanged, so both sides must match, and it's
    hashed into the frame like an encoding's parameters.
  - `scope`, `newer_consumer` and `same_version_differs` decide what each side
    accepts, and each side applies its own. A refusal's reason code says which
    side refused and why: a different line, the same version with a different
    shape, an unknown protocol, or a different encoding.
- **One handshake per connection.** A protocol can't override the handshake
  or its parameters for itself. Protocols sharing a connection must declare
  the same one, as they must for framings.
- **`degrade` covers functions first.** Refusing locally to send an enum
  variant a peer can't read (the enum caveat in the
  [compatibility rules](schema-compatibility.md)) follows later, with the
  explicit variant values of
  [core#126](https://github.com/ComlineProject/core/issues/126).
- **A weaker policy gives up a guarantee,** through the
  [existing mechanism](#giving-up-a-guarantee): core infers it from the
  parameters. `same_version_differs = "warn"` gives up **version honesty**, and
  `none`, or a custom handshake that checks nothing, gives up **schema
  agreement**. The default settings need nothing extra.
- **Changing a parameter:** a stricter policy is a patch. A weaker one gives
  something up, and adding `@unverified` is already major.

## Giving up a guarantee

> **Built for handshakes** ([core#132](https://github.com/ComlineProject/core/pull/132)):
> `@unverified`, the frozen set, its diagnostics, the version comparison and
> `accept_unverified`, and `comline accept` / `comline add` asking before they
> write it ([cli#89](https://github.com/ComlineProject/cli/pull/89)).
> The editor reports an unaccepted dependency on its `config.idp` entry, with
> a quick fix
> ([language-server#78](https://github.com/ComlineProject/language-server/pull/78)).
> Encodings without vectors and lowered bumps join when third-party encodings
> exist, and when releases can lower a bump.

Between peers, Comline gives four guarantees, each established by something
specific:

| Guarantee | Established by |
|---|---|
| **Schema agreement:** both ends were built from compatible schemas | the `comline@N` handshake |
| **Encoding agreement:** both ends use the same format and framing | the handshake |
| **Encoding conformance:** an implementation encodes what its name promises | conformance vectors behind its profile |
| **Version honesty:** a version bump says what the change breaks | the [version comparison](schema-compatibility.md) |

An extension can leave one of them unestablished. The author then vouches for
whatever replaces it ([core#121](https://github.com/ComlineProject/core/issues/121)):

1. **A handshake that doesn't establish schema or encoding agreement:** `none`,
   or a custom handshake that doesn't do Comline's checks.
2. **An encoding with no proof:** a format or framing whose profile is declared
   without vectors, or that has no profile at all. Encoding conformance is
   given up.
3. **Accepting a breaking change without a major bump:** version honesty is
   given up ([schema compatibility](schema-compatibility.md)'s open escape
   hatch).
4. **Skipping the handshake at a call site:** the hand-wired paths without one
   are renamed `Client::new_unverified` / `Server::serve_unverified`, so
   skipping there is as explicit as in a schema.

### The marker: `@unverified`

Decided in [Marking a given-up guarantee](guarantee-marker/index.md)
(Proposal C):

```ids
@handshake = "com.acme.legacy-hello@1"
@unverified = "the 2009 gateway has no schema; its version is pinned by contract"
protocol Billing {
    function charge(order: Order) -> Receipt;
}
```

- **One marker, with a reason.** The author doesn't name the guarantees.
- **Core works out the set** from what it already knows:
  - the handshake's profile, for schema and encoding agreement;
  - whether each encoding has vectors, for conformance;
  - the version comparison itself, for version honesty.

  Naming the guarantees would only repeat what core computes.
- **The set is frozen** into the compiled schema with the reason. Diagnostics,
  hover and generated docs name it, using the four guarantee names as fixed
  vocabulary: *"`Billing` is unverified: schema agreement isn't established
  (handshake `com.acme.legacy-hello@1`)"*.

### The rules

- **A reason is mandatory.** It's frozen into the compiled schema and shown to
  every consumer.
- **Off by default.** The marker is gated like `@framing` is today, through
  `settings`. Cross-package settings let an organisation forbid it everywhere.
- **Required where it applies.** Giving up a guarantee without the marker is a
  build error. A marker where nothing is given up is a warning, like an unused
  `unsafe`.
- **Consumers accept it, per protocol, and the acceptance records the set.**
  A package that depends on, or imports, such a protocol from another package
  names it in its own `config.idp`, under the dependency. Until it does, the
  build fails. The acceptance records the set of guarantees it was given for,
  so a dependency update that gives up another one stops the build again until
  it's accepted too. Using one is always a choice written down by the
  consumer, never inherited.
- **Visible everywhere.**
  - **The compiled schema** records the marker and its reason.
  - **Build output, editor hover and generated docs** show it.
  - **Generated code** documents it on the client and the dispatcher.
- **Major in the [version comparison](schema-compatibility.md):** giving up a
  guarantee is major, since peers relied on it, and so is the set growing
  ("`Billing` now also gives up schema agreement"). Restoring one is minor.

### At the package level

Decided 2026-10-20 ([core#121](https://github.com/ComlineProject/core/issues/121)).
Some cases aren't on a protocol:

- **An encoding without vectors:** the reason goes where the encoding is
  declared in `config.idp`:

  ```
  framings = {
      "legacy" = {
          encoding = "com.acme.legacy@1"
          unverified = "no vectors yet; tested by hand against the 2009 gateway"
      }
  }
  ```

- **Lowering a bump:** a decision about one release, made with
  `comline release --lower … --reason "…"` and stored on the release record
  ([Builds and releases](schema-compatibility.md#builds-and-releases)), not in
  `config.idp`.
- **A consumer's acceptance,** under the dependency in its own `config.idp`:

  ```
  dependencies = {
      billing = {
          path = "../billing"
          accept_unverified = {
              Billing = ["schema_agreement"]
          }
      }
  }
  ```

  - The list is the set accepted, a snapshot, so the build stops again if
    the set grows. It's the one place guarantee names are written; on the
    producer's side core works them out.
  - **Nobody types it by hand:** the build error offers a quick fix, and
    `comline accept billing::Billing` writes the entry, as ids are written
    into the source on build.
- **Diagnostics:** given-up guarantees get their own code family
  (`unverified::schema-agreement`, …) under `diagnostics.<code>.level`, so an
  organisation can raise the informational warnings to errors or quiet them.
  The "not accepted" error can't be lowered: if it could, accepting would
  mean nothing.

## Transports and dispatchers

Neither changes what's on the wire, so neither needs a name, a profile or a
declaration.

**Transports stay invisible to the handshake** (decided 2026-10-31). They don't
change the bytes a format or framing produces, so they need no name, profile or
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

Decided 2026-10-31 ([core#8](https://github.com/ComlineProject/core/issues/8),
[Proposal D](codegen-architecture/target-language-plugins.md)): generators
outside the CLI speak **one stdio protocol**.

- **The request:** a generator gets the compiled IR (the existing CBOR IR, with
  its core-owned IR format stamp) plus the generation request on stdin.
- **The reply:** it writes the generated files on stdout.
- **Packaging:** a generator ships either as a native executable or as a WASI
  `.wasm` (stdin and stdout).
  - The CLI runs a `.wasm` under wasmtime, sandboxed.
  - The playground runs it through a browser WASI shim. That removes the blocker
    on Proposal D: the playground can't spawn processes.
- **Compatibility:** a generator declares which IR format stamps and which
  protocol version it accepts. The CLI refuses a mismatch with a clear message.
- **Discovery** (proposed default, still to be confirmed in the implementation
  plan): `comline.toml`'s `[[generate.target]]` names a built-in by language id,
  a local path, or a registry package name.
- **The official generators use the same protocol.** The Rust and TypeScript
  generators stay linked into the CLI for speed, but are called through the same
  request and response types, so the public protocol is exercised every day.
  This is the encodings principle again: official means maintained here, not a
  private path.

Nothing about encodings depends on this. The two meet when a third-party
language wants a third-party encoding, and the `comline.toml` mapping already
covers that.

## Part of the 1.0 promise

The extension API and the generator protocol are part of 1.0, so they're
designed, built and frozen first. See [Ready for 1.0](../conduct/readiness.md).

## Open questions

None open. Both were decided on 2026-10-31:

- **Shipping implementations:** an encoding package's suggested mapping carries
  the implementation's package and version
  ([How generated code reaches one](#how-generated-code-reaches-one)).
- **Transports in the handshake:** they stay invisible
  ([Transports and dispatchers](#transports-and-dispatchers)).

## What it touches

- **runtime:**
  - the public corpus and profile spec;
  - `Handshake` as a trait, `comline@1` and `none` as official handshakes, and
    the call-site skip renamed `*_unverified`;
  - the conformance runner as a library;
  - a transport guide;
  - the dispatcher-wrapping pattern.
- **core:**
  - `config.idp` declarations of defined encodings (building on
    [core#117](https://github.com/ComlineProject/core/issues/117));
  - names declared by dependencies accepted in `@framing` and in declared
    formats;
  - `@handshake`;
  - the marker for a given-up guarantee: its gate, its required-where-it-applies
    rule, and the consumer's acceptance.
- **cli:**
  - the per-target mapping in `comline.toml`, including the implementation's
    package and version;
  - the generator protocol: running native and `.wasm` generators (wasmtime),
    and refusing a format-stamp or protocol-version mismatch.
- **generation**, **comline-rust** and **comline-typescript:** mapped types wired
  into generated code; an unmapped encoding is an error.
- **language server:** a given-up guarantee shown on hover, and the acceptance
  an importing package lacks offered as a fix.
- **playground:** a browser WASI shim to run `.wasm` generators.
- **docs:** a guide to writing each extension, and the generator protocol.

## What shipped

Built in October 2026. The guides are under
[Extending Comline](../guide/extending/index.md), the
[generator protocol](../reference/generator-protocol.md) and the
[conformance spec](../reference/conformance.md) are reference pages.

- **Declaring encodings:** `encodings` in `config.idp`, with a kind, a profile
  and suggested mappings
  ([core#142](https://github.com/ComlineProject/core/pull/142)); the official
  ones, declared by an embedded package ([core#143](https://github.com/ComlineProject/core/pull/143));
  core's parser behind a feature, for an IR-only build
  ([core#144](https://github.com/ComlineProject/core/pull/144)).
- **Mapping to a target:** `encodings` in `comline.toml`
  ([cli#105](https://github.com/ComlineProject/cli/pull/105)), resolved with
  the override, then the declaration, then an error
  ([generation#88](https://github.com/ComlineProject/generation/pull/88)); the
  Rust and TypeScript generators emit the mapped types
  ([comline-rust#80](https://github.com/ComlineProject/comline-rust/pull/80),
  [comline-typescript#92](https://github.com/ComlineProject/comline-typescript/pull/92)).
- **Handshakes:** the async handshake and
  `AsyncConnection::connect_with` / `accept_with`
  ([runtime#65](https://github.com/ComlineProject/runtime/pull/65)); generated
  code runs a namespaced handshake wherever it opens
  ([comline-rust#81](https://github.com/ComlineProject/comline-rust/pull/81),
  [comline-rust#82](https://github.com/ComlineProject/comline-rust/pull/82),
  [comline-typescript#93](https://github.com/ComlineProject/comline-typescript/pull/93)).
- **Profiles and vectors:** the conformance runner as a library, and the corpus
  as a versioned spec ([runtime#69](https://github.com/ComlineProject/runtime/pull/69));
  `comline conformance` ([cli#108](https://github.com/ComlineProject/cli/pull/108)).
- **Generators:** the generator protocol
  ([generation#85](https://github.com/ComlineProject/generation/pull/85)); the
  Rust and TypeScript generators as stdio processes
  ([comline-rust#79](https://github.com/ComlineProject/comline-rust/pull/79),
  [comline-typescript#91](https://github.com/ComlineProject/comline-typescript/pull/91));
  external native and `.wasm` generators in the CLI, with the built-ins going
  through the protocol ([cli#104](https://github.com/ComlineProject/cli/pull/104));
  a WASI shim and a terminable, capped runner in the playground
  ([playground#103](https://github.com/ComlineProject/playground/pull/103),
  [playground#106](https://github.com/ComlineProject/playground/pull/106)).
- **Transports:** the TypeScript contract that `send` lends the frame until it
  resolves ([comline-typescript#88](https://github.com/ComlineProject/comline-typescript/pull/88)).
- **Guides:** the pages linked above.

Where it differs from the text, or isn't built:

- **Registry names are deferred.** Naming an encoding package or a generator by
  a registry package, rather than a path or a dependency, waits for the
  registry (recorded on [core#8](https://github.com/ComlineProject/core/issues/8)).
  A generator is named by a path in `comline.toml`.
- **The facts a handshake gets** are the schema fingerprint, the format and
  framing names and the capability bits. The package version and per-protocol
  lines come with the handshakes that use them.
- **An encoding without vectors** is allowed, but core doesn't yet record it as
  a given-up guarantee, and the package-level `unverified` reason on an
  encoding isn't built. Core infers a given-up set only from the `none`
  handshake today.
- **Third-party profiles in the version comparison** wait on the compatibility
  rules ([Schema compatibility](schema-compatibility.md)), which are still a
  proposal.
- **Dispatchers** are wrapped by implementing `Dispatch` yourself; the runtime
  has no helper for composing wrappers.
- **The playground's interface** doesn't reach external generators yet; its
  runner does.
