# Runtime & codegen repository organization

**The question.** Comline's per-language surface has three parts: the **code
generator** (frozen IR → source), the **library generator** (manifest + FFI
wrapper so the ecosystem can load it), and the **runtime** (the library the
generated code calls at execution time). As languages are added, how should
those parts be split across repositories?

Today they are all in two mono-repos — `generation` (both generators) and
`runtime` (core runtime + every binding + std-extra) — and each new language
drops its native toolchain into that one workspace. That cost is linear in the
number of languages and is starting to bite.

Two proposals answer it differently:

| | Splits by | In one line | Status |
|---|---|---|---|
| [Proposal A — split by concern](split-by-concern.md) | **concern** | `generation` stays one repo; `runtime` graduates heavyweight language runtimes to their own repos as each earns it | accepted — current direction |
| [Proposal B — split by language](split-by-language.md) | **language** | one repo per target (`comline-python`, …) holds that language's codegen, libgen, and runtime together | under discussion |

It comes down to where you put the seam. **A** cuts between the build-time
tooling and the shipped runtime — one repo for all the generators, one (then a
few) for the runtimes. **B** cuts between languages — one repo per language with
its whole stack inside, and the tooling and the runtime sharing that repo.

Both proposals are written to the same shape — **Shape · The case for it · The
case against · Prior art · When this would be the right call** — so they can be
read side by side.

**They can also combine.** gRPC and Protocol Buffers are Proposal A at the top
level — a core mono-repo plus a graduated repo per heavyweight language — but
each graduated repo (`grpc-go`, `protobuf-go`) is itself organised like Proposal
B, with that language's codegen and runtime together. "A now, B inside the repos
that graduate" is a real option.

The org-wide decision record, with the full options analysis (A–F) and the
phased rollout, is
[Design → Runtime & generation repository structure](../../design/runtime-repo-structure.md).

## Prior art at a glance

How projects in this space actually organise their repos, scored against the
same six traits. Both proposals reference these; here they are side by side.

*✓ yes · ◐ only some languages · ✗ no*

### Apache Thrift

The compiler and every `lib/<language>` implementation live in one repository,
[`apache/thrift`](https://github.com/apache/thrift). Nothing is split out.

| Trait | |
|---|:--:|
| Language-neutral core in its own repo | ✗ |
| Code generators centralized in one repo | ✓ |
| One repo per target language | ✗ |
| A language's codegen + runtime bundled as one unit | ✗ |
| Heavy languages graduate, light ones stay bundled | ✗ |
| Single repo: compiler + every language | ✓ |

### Protocol Buffers

[`protocolbuffers/protobuf`](https://github.com/protocolbuffers) carries `protoc`
and the C++, Java, Python, C#, Ruby, PHP and Objective-C runtimes; Go
(`protobuf-go`) and JavaScript (`protobuf-javascript`) have their own repos, each
pairing that language's `protoc` plugin with its runtime.

| Trait | |
|---|:--:|
| Language-neutral core in its own repo | ✗ |
| Code generators centralized in one repo | ◐ |
| One repo per target language | ◐ |
| A language's codegen + runtime bundled as one unit | ◐ |
| Heavy languages graduate, light ones stay bundled | ✓ |
| Single repo: compiler + every language | ✗ |

### gRPC

[`grpc/grpc`](https://github.com/grpc) holds the C core and the C++, Python,
Ruby, PHP and Objective-C wrappers; Java, Go, Node, C#, Swift, Kotlin, Dart and
Web each have their own repo, each bundling that language's `protoc` plugin with
its runtime.

| Trait | |
|---|:--:|
| Language-neutral core in its own repo | ✗ |
| Code generators centralized in one repo | ✗ |
| One repo per target language | ◐ |
| A language's codegen + runtime bundled as one unit | ✓ |
| Heavy languages graduate, light ones stay bundled | ✓ |
| Single repo: compiler + every language | ✗ |

### Cap'n Proto

[`capnproto/capnproto`](https://github.com/capnproto) is the C++ compiler and
runtime; every other language (`capnproto-rust`, `capnproto-java`, …) is its own
repo holding that language's compiler plugin, runtime and RPC layer.

| Trait | |
|---|:--:|
| Language-neutral core in its own repo | ✗ |
| Code generators centralized in one repo | ✗ |
| One repo per target language | ✓ |
| A language's codegen + runtime bundled as one unit | ✓ |
| Heavy languages graduate, light ones stay bundled | ✗ |
| Single repo: compiler + every language | ✗ |

### Smithy

[`smithy-lang/smithy`](https://github.com/smithy-lang) is the language-neutral
model and validation; `smithy-rs`, `smithy-typescript`, `smithy-go`,
`smithy-swift`, `smithy-kotlin`, `smithy-python` and others each hold that
language's code generator and runtime libraries.

| Trait | |
|---|:--:|
| Language-neutral core in its own repo | ✓ |
| Code generators centralized in one repo | ✗ |
| One repo per target language | ✓ |
| A language's codegen + runtime bundled as one unit | ✓ |
| Heavy languages graduate, light ones stay bundled | ✗ |
| Single repo: compiler + every language | ✗ |

### Reading the grid

- **Thrift** — one repo for everything. The arrangement Comline is on now and
  wants to leave.
- **Smithy**, **Cap'n Proto** — every language gets its own full-stack repo,
  uniformly. That's **Proposal B**.
- **gRPC**, **Protocol Buffers** — a core mono-repo plus a graduated repo for
  each heavyweight language. That's **Proposal A** — and inside each graduated
  repo, codegen and runtime sit together, which is Proposal B one level down.
- Only Smithy keeps the neutral core in its own repo. Comline already does too
  (`core`), so that row is settled regardless of which proposal wins.
