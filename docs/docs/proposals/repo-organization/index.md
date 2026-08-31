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

Two proposals answered it differently. **Proposal B is now accepted** — the
design record adopts it directly, reversing an earlier phased plan.

| | Splits by | In one line | Status |
|---|---|---|---|
| [Proposal A](split-by-concern.md) | **Concern** | `generation` stays one repo; `runtime` graduates heavyweight language runtimes to their own repos as each earns it | rejected — superseded by B |
| [Proposal B](split-by-language.md) | **Language** | one repo per target (`comline-python`, …) holds that language's codegen, libgen, and runtime together | **accepted** |

It comes down to where you put the seam. **A** cuts between the build-time
tooling and the shipped runtime — one repo for all the generators, one (then a
few) for the runtimes. **B** cuts between languages — one repo per language with
its whole stack inside, and the tooling and the runtime sharing that repo. B won
on two points: the codegen ↔ runtime agreement becomes a same-repo, same-CI
invariant, and there is no recurring "is this language heavy enough to graduate"
call to make.

Both proposals are written to the same shape — **Shape · The case for it · The
case against · Example projects · When this would be the right call** — so they
can be read side by side. Each **Example projects** section scores real projects
(Thrift, Protocol Buffers, gRPC, Cap'n Proto, Smithy) against the same six repo
traits.

**Proposal A isn't wasted context.** gRPC and Protocol Buffers are A at the top
level — a core mono-repo plus a repo per heavyweight language — but each of those
per-language repos (`grpc-go`, `protobuf-go`) is itself organised like B. The
per-language repo is where the industry converges either way.

The org-wide decision record, with the full options analysis (A–F), is
[Design → Runtime & generation repository structure](../../design/runtime-repo-structure.md).
