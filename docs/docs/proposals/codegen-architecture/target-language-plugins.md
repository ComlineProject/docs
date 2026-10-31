# Proposal D — target-language plugins

Status: **implemented** (decided 2026-10-31) · See the
[section overview](index.md) for the question all five answer ·
tracked in [core#8](https://github.com/ComlineProject/core/issues/8)

**As built:** see [What shipped](../extensibility.md#what-shipped), the
[generator protocol](../../reference/generator-protocol.md) and the
[guide](../../guide/extending/generators.md). Discovery is by path; naming a
generator by a registry package waits for the registry
([core#8](https://github.com/ComlineProject/core/issues/8)).

**Chosen form:** a stdio protocol with native or WASI packaging, not
`protoc`-style native processes only. See [The decision](#the-decision).
The sections after it are the case as it was argued.

**The idea:** Comline stops generating code. It compiles schemas, serialises
the request, and hands it to a plugin program — which may be written in any
language, most usefully the target's own. `protoc`'s model.

## The decision

Decided 2026-10-31. The shape below stands, with these choices:

- **One stdio protocol.** A generator gets the compiled IR (the existing CBOR
  IR, with its core-owned IR format stamp) plus the generation request on
  stdin. It writes the generated files on stdout.
- **Native or WASI packaging.** A generator ships either as a native executable
  or as a WASI `.wasm` (stdin and stdout).
- **Sandboxed `.wasm`.** The CLI runs it under wasmtime. The playground runs it
  through a browser WASI shim, which removes the blocker named under
  [the case against](#the-case-against): the playground can't spawn processes.
- **Versions are checked.** A generator declares which IR format stamps and
  which protocol version it accepts. The CLI refuses a mismatch with a clear
  message.
- **Discovery** (proposed default, still to be confirmed in the implementation
  plan): `comline.toml`'s `[[generate.target]]` names a built-in by language id,
  a local path, or a registry package name.
- **The official generators use it too.** Rust and TypeScript stay linked into
  the CLI for speed, but are called through the same request and response types.
  The public protocol is exercised every day.
- **Part of 1.0.** See [Ready for 1.0](../../conduct/readiness.md) and
  [Extending the call system](../extensibility.md#generators).

## Shape

```
comline generate
  ├─ compile schemas -> frozen IR
  ├─ serialise GenRequest  (CBOR — core already speaks it)
  └─ for each target:
       spawn `comline-gen-<lang>`, write request to stdin,
       read a file set back from stdout, write it to disk

comline-gen-typescript/     a Node package using ts-morph or the
                            TypeScript compiler's own factory API
comline-gen-python/         a Python package using ast / libcst
comline-gen-rust/           stays Rust, built in-process as today
```

The plugin contract becomes a **versioned wire format** rather than a Rust
trait: the same role `GenRequest` plays now, but serialisable and stable
across languages.

## The case for it

- **Each generator is written where its expertise lives.** A TypeScript
  emitter authored in TypeScript can use `ts-morph` or the compiler's factory
  API — strictly better tools than anything reachable from Rust, and the
  people most able to judge idiomatic output can contribute without learning
  Rust.
- **It retires the pin cascade.** Today `comline-core`'s rev is pinned at
  fourteen sites across seven repositories — `generation` alone holds five —
  and every generator change walks an ordered cascade, three of them in a
  single working session.
  Cargo refuses to unify two git dependencies unless the rev strings match
  byte for byte, so this is structural, not sloppiness. A wire contract
  replaces it with ordinary version negotiation.
- **Release cycles decouple.** A generator ships on its own schedule, and a
  new language needs no change to the CLI, no cargo feature, and no
  coordination.
- **It is the proven path to breadth.** Every schema compiler that reached
  many languages did this.
- **It composes with [A](resolution-kernel.md).** The resolved model can be
  *part of the serialised request*, so plugins inherit the resolution work
  instead of each re-deriving it — which is the failure mode of protoc
  plugins, where each re-invents naming and imports.

## The case against

- **The wasm playground blocks it** (resolved by WASI packaging, see
  [The decision](#the-decision)). `playground/wasm` compiles the generators
  to wasm32 and runs them in the browser, on purpose — its manifest states the
  playground runs *that* code, "not a re-implementation." A browser cannot
  spawn `comline-gen-typescript`. Keeping the playground would mean either a
  server round-trip, abandoning the "same code" guarantee, or shipping each
  plugin as a wasm module — which the component model may eventually make
  reasonable, but not comfortably today.
- **It trades one install problem for another.** `comline generate` currently
  needs nothing but itself. Under D, generating TypeScript needs Node present
  and the right plugin version installed. For a tool whose selling point is a
  single binary, that is a real regression in the common case.
- **A wire contract is a much harder thing to change than a Rust trait.**
  `GenRequest` has gained fields three times recently — `default_framing`,
  `lang_version`, `external_std` — each a one-line change with a compiler to
  catch every consumer. As a cross-language wire format, each of those is a
  compatibility negotiation.
- **It is the largest rework of the five**, and it is mostly protocol
  engineering rather than better generated code.
- **Fewer shared invariants.** The accepted
  [split-by-language](../repo-organization/split-by-language.md) proposal put
  codegen and runtime in one repo precisely so their agreement is a same-CI
  invariant. Plugins in different languages weaken that.

## Example projects

| Project | Plugins? | Notes |
|---|---|---|
| **Protocol Buffers / Buf** | yes | `CodeGeneratorRequest` on stdin; plugins in Go, TypeScript, Rust, Swift, …; the canonical design |
| **Cap'n Proto** | yes | `capnpc-<lang>` executables; `capnpc-rust` is Rust |
| **gRPC** | yes | per-language plugins alongside protoc |
| **Smithy** | no | one JVM framework generating every target |
| **wit-bindgen** | no (in-process) | a Rust core with per-language bindgen crates — closer to [A](resolution-kernel.md), and notably the most *recent* of these designs |

Worth noting that the newest entrant, built for a polyglot wasm world, chose
the in-process kernel rather than the plugin protocol.

## When this would be the right call

*Superseded by [The decision](#the-decision): accepted on 2026-10-31. What follows is the original reasoning.*

When the number of target languages passes the point where Rust-authored
emitters stop being credible — plausibly around five or six, or the first time
a language's idioms need a native expert — **and** the playground requirement
has been resolved, either by accepting a server round-trip or by wasm plugins
becoming routine.

Until then the useful action is preparation, not adoption: keep the kernel's
request boundary serialisable, so this stays a port rather than a rewrite.
