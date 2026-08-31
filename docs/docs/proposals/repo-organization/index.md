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

Both are written to the same shape — **Shape · The case for it · The case
against · Prior art · When this would be the right call** — so they can be read
side by side, and each cites real projects built that way.

**They can also combine.** gRPC and Protocol Buffers are Proposal A at the top
level — a core mono-repo plus a graduated repo per heavyweight language — but
each graduated repo (`grpc-go`, `protobuf-go`) is itself organised like Proposal
B, with that language's codegen and runtime together. "A now, B inside the repos
that graduate" is a real option.

The org-wide decision record, with the full options analysis (A–F) and the
phased rollout, is
[Design → Runtime & generation repository structure](../../design/runtime-repo-structure.md).
