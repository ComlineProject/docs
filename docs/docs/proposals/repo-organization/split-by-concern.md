# Proposal A — split by concern

Status: **accepted** — the direction the current
[design record](../../design/runtime-repo-structure.md) follows · Re-examined
against [Proposal B — split by language](split-by-language.md) · See the
[section overview](index.md) for the question both answer.

**The idea:** the generator and the runtime are different kinds of software, so
draw the repo lines along *that* boundary rather than along languages. All the
code and library generators live in one repo (`generation`). The runtime lives
in another (`runtime`) that starts out holding everything and only spins a
language's runtime off into its own repo once that language actually needs it.

The full options analysis and the phased rollout are in the
[design record](../../design/runtime-repo-structure.md); this page is the case
for going this way.

## Shape

Two repos, cut at the line between "language-agnostic core" and "per-language
parts".

**`generation` stays one repo, probably forever.** Writing a code generator is
mostly string formatting — the TypeScript one we already have is small and has
no unusual dependencies. Library generation adds some manifest templating and,
for `dylib`, a bit of FFI tooling (`cbindgen`, `abi_stable`). None of that is
heavy, so there's no reason to split it up:

```
generation/
  crates/codegen        comline-codelib-gen — every `code` generator
                        (rust, typescript, python, lua, luau, …); pure string emission
  crates/lib-rust       `lib` / `dylib` for rust — cbindgen, abi_stable      ┐ non-default
  crates/lib-python     `lib` for python — pyproject templating              │ members, pulled
  crates/lib-lua        `lib` for lua — rockspec templating                  │ in by the CLI
  crates/lib-node       `lib` for node — package.json + napi glue            ┘ behind features
```

A plain `cargo build` builds `codegen` and nothing else; each `lib-*` crate is
opt-in with its own CI job, so a change to the Python lib generator never builds
the Lua one. The registry that maps a language name to its generator moves into
the CLI behind cargo features once the first `lib-*` crate exists — details in
[Design → Generation](../../design/generation.md#generator-crate-layout).

**`runtime` starts as one repo and sheds weight over time.** A language binding
stays in `runtime` as long as it's cheap to keep there. It moves out when it
needs to ship to its own registry on its own schedule, or when someone outside
the core team takes ownership of it:

```
Now → Step 1 (in place, one repo):
runtime/
  crates/runtime        comline-runtime — `std` is a feature; the core_no-std fork is gone
  crates/std-extra      comline-runtime-std-extra — opt-in, out of the core build graph
  langs/c  langs/lua  langs/luau  langs/python
                        opt-in members; one CI job per language
  conformance/          schema + expected-behaviour corpus every runtime must pass

End state:
runtime/                comline-runtime + the light bindings (c, lua, luau)
runtime-python/         graduated — pyo3, PyPI wheels, its own release schedule
runtime-node/           napi, npm (starts out on its own)
runtime-<lang>/         … as each earns it
```

So the org grows by about **one repo per genuinely heavy language** — Python,
Node, maybe Go or Swift down the line — not one per language.

**How the two stay in sync.** Generated code imports the runtime, so the library
generator for a language writes a manifest (`Cargo.toml`, `pyproject.toml`, and
so on) that pins a compatible `comline-runtime` version. `generation` keeps a
small per-language table of "runtime package name, version range" that tracks
the `core ↔ runtime` contract. It's data in a table, not a code dependency
between the repos:

```
runtime releases vX
        │
        ▼
core ↔ runtime contract doc:  "IR feature Y needs runtime ≥ vX"
        │
        ▼
lib generator for X emits:    depends on comline-runtime-X  ">= vX"
```

## The case for it

**It matches how the two are actually built and used.** The generator is a build
tool. It runs on a developer's machine during `comline generate`, writes some
files, and is never shipped anywhere. The runtime is the opposite — it ends up
as a dependency in someone's real application, published to PyPI or npm or
crates.io. The two get changed for different reasons, released on different
schedules, and a CVE in one means something completely different from a CVE in
the other. Separate repos line up with that reality; one repo papers over it.

**The expensive parts stay quarantined.** Almost all the weight is on the
runtime side. A Python *runtime* needs pyo3, CPython headers, and a wheel build
matrix across Python versions and operating systems. A Python *generator* needs
none of that. If they share a workspace, everyone who touches the toolchain pays
the CPython cost for no reason. Keep them apart and the generator repo stays
light no matter how long the language list gets.

**No repo explosion.** Plenty of bindings are cheap to maintain — Lua, Luau, C.
Those never need their own repo; they sit in `runtime` behind a feature flag and
a CI job. Only the heavy ones move out. Twelve languages doesn't mean twelve
repos, it means `runtime` plus two or three spin-offs.

**Each side moves at its own pace.** The generator can ship a fix without
waiting on a runtime release. A graduated `runtime-python` can cut a patch
release for a new-CPython wheel without anything else being involved.

## The case against

**Some changes naturally want both repos at once.** Add an IR feature like
streaming responses and you probably need the generator to emit new code *and*
the runtime to handle the new call shape. Here that's two PRs across two repos
plus a bump to the contract doc, done in order. One repo would have been one PR.

**The link between the two is soft.** The generator writes "depends on
comline-runtime >= 1.4" into a manifest, but nothing verifies that's true at
build time. If the generator and the runtime drift apart, the only thing that
notices is the conformance suite. A hand-maintained "which runtime version does
this generator target" table is exactly the kind of thing that quietly goes
stale.

**"Where's the Python code" has two answers.** The generator is in `generation`,
the runtime is in `runtime` or `runtime-python`. Anyone chasing an end-to-end
Python bug is working across repos and keeping two checkouts aligned.

**"Has this language earned its own repo yet" is a judgement call every time.**
There's no bright line, so each new heavy language reopens the same discussion.

## When this would be the right call

This is the conservative option, and it fits where the project is now: a core
team that owns the whole toolchain, a language list that's mostly lightweight
bindings, and no appetite for standing up a repo, a release pipeline, and a CI
matrix for every language. It keeps per-language repos available as a later move
without committing to them up front. If the language list is going to stay
small-to-medium and mostly light, this is the pragmatic choice.
