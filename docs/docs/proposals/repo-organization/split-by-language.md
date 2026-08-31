# Proposal B — split by language

Status: **under discussion** · Alternative to
[Proposal A — split by concern](split-by-concern.md) (the direction the current
[design record](../../design/runtime-repo-structure.md) follows) · This is Option
**E** from that record, written up in full · See the
[section overview](index.md) for the question both answer.

**The idea:** one repo per target language. `comline-python` holds the Python
code generator, the Python library generator, the Python runtime, and any
Python-specific standard-library extras — all together. `core` stays
language-neutral, and `generation` shrinks to a shared helper crate that every
language repo depends on.

## Shape

```
comline-python/
  codegen/       the Python `code` generator (Rust) — frozen IR → .py sources
  libgen/        the Python `lib` generator (Rust) — pyproject.toml, FFI wrapper
  runtime/       comline-runtime-python — Rust core runtime + pyo3 glue
  std-extra/     Python-only runtime std additions
  conformance/   this target's schema → behaviour tests, one CI run

comline-lua/     … the same five directories
comline-node/    …
```

The only things every language repo shares are `core` (the language-agnostic IR
and compiler) and a small `comline-codegen` support crate — the `GeneratedFile`
type, the generator interface, the IR-walking helpers.

## The case for it

**The generator and the runtime have to agree, and here that's checked in one
place.** The generated Python code calls into the Python runtime across an FFI
boundary, so the two sides have to line up exactly. Put them in the same repo
and the same CI run builds the generator, runs it, builds the runtime, and runs
the generated code against it — on every PR. No version table, no contract doc,
no "did we remember to update the other repo". If the two don't match, CI is
red, right there.

**One obvious home per language.** Someone who wants to improve Python support
clones `comline-python` and it's all in front of them. No cross-repo checkouts,
and no guessing whether a bug is in the generator or the runtime — both are in
the same tree.

**Native tooling, end to end.** `comline-python`'s CI already has CPython,
maturin, and pytest set up, so the library-generator tests can build the wheel
they generate and actually import it. That kind of real end-to-end check is
awkward when the generator lives off in a Rust-only repo.

**Adding a language is copying a template.** A new target is a new repo from a
template. It doesn't touch any existing repo, doesn't destabilise a shared
workspace, and doesn't need anyone to wire up feature flags.

**Everything about a language is independent** — version numbers, release
cadence, issue tracker, even the licence if some ecosystem is fussy about it.

## The case against

**It bundles a build tool with a shipped library just because they share a
language.** The code generator runs inside the toolchain on a developer's
machine; the runtime ships to end users. Different audiences, different release
rhythms, different security exposure — and now they're in one repo with one
version number and one release.

**The repo ends up bilingual with two toolchains.** The Python code generator is
light Rust that emits strings. Sitting it next to pyo3 and a CPython build means
every CI run pulls in both, even for a change that only touches string
formatting.

**The shared codegen layer fragments.** Every language repo still depends on
`comline-codegen`. Change that interface and you're rolling it out across every
language repo, one at a time — the same cross-repo coordination this layout was
meant to avoid, just moved from the runtime side to the codegen side.

**The CLI depends on a crate from every language repo.** `comline generate` has
to know about all of them, so the CLI pulls N generator crates from N repos, and
a release of any one of them can move the CLI's lockfile.

**You still need a cross-language test suite somewhere.** "Do the Rust and
Python generators treat an optional field the same way?" can't be answered
inside a single language repo. That needs a corpus spanning all of them, and no
one repo naturally owns it.

**An IR change hits every repo.** Change something in `core` and you're updating
every `comline-<lang>` against it. The `core` ↔ target boundary becomes a public
API you have to version carefully, because a lot of repos consume it.

## Prior art

**Smithy** — the IDL and SDK-generation framework behind the AWS SDKs — is built
exactly this way. The language-neutral model tooling is in `smithy-lang/smithy`;
then `smithy-lang/smithy-rs`, `smithy-typescript`, `smithy-go`, `smithy-swift`,
`smithy-kotlin`, `smithy-python` and others each hold **both** the code
generator and the runtime libraries for that one language. AWS generates every
one of its SDKs from this layout.

**Cap'n Proto** does it for every language except its C++ reference.
`capnproto/capnproto` is the C++ compiler and runtime; `capnproto/capnproto-rust`
bundles the `capnpc` compiler plugin, the `capnp` runtime and the RPC layer;
`capnproto/capnproto-java` bundles its plugin and its runtime. Each language repo
carries its whole stack.

**protobuf-go and grpc-go** show that even mono-repo-first projects organise
their *graduated* languages this way. `protocolbuffers/protobuf-go` ships
`protoc-gen-go` next to the `google.golang.org/protobuf` runtime;
`grpc/grpc-go` ships `protoc-gen-go-grpc` next to the gRPC runtime. Codegen and
runtime for the language, in one repo.

**Serde** and **kotlinx.serialization** are the single-language version of the
idea: the code generator — a derive macro, a compiler plugin — ships alongside
the runtime library, `serde` with `serde_derive`, the kotlinx.serialization
plugin with its core.

## When this would be the right call

Once each language genuinely has its own maintainer or team, ecosystem-native
packaging is non-negotiable across the board, and the `core` ↔ target contract
has settled enough to be a real versioned API — at that point a per-language
repo isn't overhead, it's just the unit people already work in. It's where
[Proposal A](split-by-concern.md) ends up for runtimes anyway; this proposal
gets there sooner and brings codegen along too.
