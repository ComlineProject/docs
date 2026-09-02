# Runtime & generation repository structure

Status: **decided — per-language target repos** (Option **E** / Proposal **B**;
reverses the earlier phased C→B recommendation) · Affects
`ComlineProject/core`, `ComlineProject/runtime`, `ComlineProject/generation`,
`ComlineProject/cli`

This page is about repo granularity for the whole per-language surface —
codegen, libgen, and runtime. The alternatives are demonstrated in full, to a
common shape, under
[Proposals → Runtime & codegen repository organization](../proposals/repo-organization/index.md):
**A — split by concern** and **B — split by language**. After writing both out,
**B (Option E) is adopted directly** — see [Decision](#decision) below.
[Generation](generation.md) covers what codegen / libgen / runtime each mean and
the `generation` cleanup that got the generators out of `core`; its "generators
stay in one repo" endpoint is superseded here.

## Problem

`ComlineProject/runtime` is a single Cargo workspace (`runtime/Cargo.toml`, one
`Cargo.lock`) holding:

- the Rust **core runtime** — `runtime/core` (`comline-runtime`, std) and
  `runtime/core_no-std`;
- **every language binding** — `runtime-langs/{c, lua, lua-test, luau, python}`,
  each a `cdylib` linking the core runtime to a language VM (mlua, pyo3,
  cbindgen, …);
- `runtime-std-extra` — optional runtime-side standard library
  (`capacity-management`, …).

Each new language drops its native toolchain into *that one* workspace: mlua
wants Lua headers, pyo3 wants a CPython, a Node binding would want napi. Every
contributor builds all of it, CI builds all of it on every push, one lockfile
couples the versions, one tag releases everything at once.

`ComlineProject/generation` has the mirror of this on the codegen side. The
de-rot got the generators out of `core` and into one `generation` repo
(`comline-codelib-gen` for `code`, per-language crates for `lib` / `dylib`). That
was the right first move, but under the decision below the per-language
generators do not stop in `generation` — they continue on into each language's
own repo, and `generation` becomes the shared support crate they all depend on.

The cost is linear in the number of languages, and it is starting to bite.

## Axes

1. **Repo granularity** — mono-repo · core + satellites · repo-per-language.
2. **Cargo workspace granularity** — one workspace · nested independent
   workspaces · per-crate manifests.
3. **Source of truth for a language runtime** — a Rust binding crate in the org,
   vs a package native to that ecosystem (a wheel on PyPI, a rock on LuaRocks,
   an npm package) that the ecosystem consumes directly.
4. **`runtime-std-extra` coupling** — bundled with the core runtime vs an opt-in
   dependency.

## Options considered

The six layouts weighed. The chosen route is **E** — one repo per target
language, adopted directly rather than phased into. **F** remains the eventual
end state, once the `core` ↔ target contract has held stable.

| | Isolation | Cross-cutting change | Ecosystem-native dist | Migration cost |
|---|---|---|---|---|
| **A** status quo mono-repo | low | one PR | no | — |
| **B** core repo + repo per language | high | spans repos | yes | medium |
| **C** one repo, independent workspaces | medium | one PR | no | low |
| **D** fold runtime into `generation` | low | one PR | no | medium |
| **E** per-language target repos (codegen+libgen+runtime) | highest | spans repos | yes | high |
| **F** contract-first, independent runtimes | n/a | spec-bound | yes | high |

### A — Status quo: one `runtime` mono-repo, one workspace

Keep `runtime/` as it is.

- **For** — atomic cross-cutting changes (core API + all bindings in one PR),
  one CI, trivial local dev, no version matrix yet.
- **Against** — cost grows linearly: everyone pulls every native toolchain, CI
  builds everything on every push, shared `Cargo.lock` and release cadence, a
  Python-only contributor still fights the Lua build, and no ecosystem can
  consume its runtime idiomatically (there is a `cdylib`, not a wheel / rock /
  npm package).

### B — Core runtime repo + one repo per language

`comline-runtime` (Rust, published to crates.io) plus `runtime-python`,
`runtime-lua`, `runtime-luau`, `runtime-c`, … each depending on a *released*
core version and owning its ecosystem packaging (PyPI, LuaRocks, npm).

- **For** — isolation (clone only what you touch); per-language CI with only
  that toolchain; independent versioning and cadence; idiomatic distribution;
  clear ownership.
- **Against** — core API changes now span repos (bump crate, release, then
  update each binding) and need a real semver + compatibility policy; more repo
  admin; onboarding friction ("where does X live"); cross-boundary integration
  testing needs orchestration.

### C — One repo, independent workspaces + path-filtered CI

Keep one `runtime` repo, split it into independent workspaces — `core/`,
`langs/python/`, `langs/lua/`, `std-extra/` — or one workspace where every
binding is a non-default member so a root `cargo build` builds core only. CI
runs one job per directory, path-filtered so a Python PR never installs Lua.

- **For** — keeps atomic changes and a single clone; removes the
  "lock everything / build everything" cost; incremental, low migration.
- **Against** — still one repo to clone (grows unboundedly); shared issue
  tracker and tag namespace unless per-component tags are added; nested Cargo
  workspaces are slightly awkward (separate lockfiles, `exclude`); no
  ecosystem-native packaging by itself.

### D — Fold `runtime` into `generation`, per language

`generation/python/{lib-gen, runtime}`, `generation/lua/{…}`, … — one directory
per language target covering both its binding generator and its runtime.

- **For** — a language contributor touches one place; "the Python target" reads
  as one unit.
- **Against** — conflates build-time tooling (codegen, internal, runs in the
  toolchain) with a shipped user-facing dependency (runtime) — different
  audiences, deps, cadence, possibly licensing; makes `generation` the new heavy
  mono-repo. Moves the weight, does not remove it.

### E — Per-language target repos

The full split: `comline-rust`, `comline-python`, `comline-lua`, … each a
complete target implementation (codegen + libgen + runtime + language-specific
extras). `core` stays language-agnostic.

- **For** — maximal isolation and ownership; a new language is a new repo from a
  template with zero impact on the others; each repo uses its ecosystem's native
  tooling end to end.
- **Against** — heaviest coordination; the core↔target contract becomes a public
  API across many repos; scaffolding duplication; cross-target consistency needs
  a shared conformance suite; org sprawl.

### F — Contract-first, independent runtimes

Publish the stable artifact: the call-system framing, the frozen-IR-to-types
mapping, and the FFI/ABI the core runtime exposes. Ship a reference Rust
runtime. Language runtimes are implemented against the spec — by the core team
or third parties — in whatever repo they like.

- **For** — scales past the core team; the heavy thing (N runtimes) is nobody's
  single burden; forces a clean, documented boundary.
- **Against** — needs the spec to exist and stay stable (large up-front doc +
  versioning work); fragmentation risk (three half-done Python runtimes);
  official-support story unclear; premature at alpha.

## Decision

**One repo per target language** — `comline-rust`, `comline-typescript`,
`comline-python`, `comline-lua`, `comline-luau`, `comline-c`, … Each holds that
language's **code generator, library generator, runtime, and language-specific
std extras** together. `core` stays language-neutral. Every target repo depends
on two language-neutral crates and nothing else from the org:

- **`comline-core`** — the IR and compiler (unchanged).
- **`comline-codegen`** — what `generation` becomes: the shared codegen support
  crate (the `GenRequest` / `GeneratedFile` contract, the IR-walk helpers, the
  generator trait). No language-specific code.

`runtime` keeps only `comline-runtime`, the language-agnostic core runtime.

**Dependency mechanism: git revs, not crates.io.** At this stage publishing is
overhead with no payoff, so `comline-core` and `comline-codegen` are consumed by
git rev — the way `generation` and `cli` already consume `core`. The cost is
coordinated rev bumps across repos (and one `comline-core` in any given tree, so
the CLI composes targets pinned to the same rev). Publishing to crates.io is a
later call, not a prerequisite for anything below.

### Why the reversal

The earlier recommendation phased **C → B** and called **E** premature. Writing
[Proposal B](../proposals/repo-organization/split-by-language.md) out in full
changed the read:

- The **codegen ↔ runtime agreement is a same-repo, same-CI invariant** here —
  one PR builds the generator, runs it, builds the runtime, and runs the
  generated code against it. The phased path deferred that and leaned on a
  hand-maintained version/rev table plus a conformance suite to catch drift.
- **"Which languages are heavy enough to graduate"** turned out to be a
  recurring judgement call. Making every language its own repo from the start
  removes the question entirely.
- The de-rot already did the hard part — the generators are out of `core`.
  Continuing them into per-language repos is a smaller step than it was a year
  ago.

### What moves where

| Repo | Becomes |
|---|---|
| `core` | unchanged — already language-neutral |
| `generation` | `comline-codegen` — shared support crate only; the `rust` and `typescript` `code` generators built during the de-rot move out to `comline-rust` / `comline-typescript` |
| `runtime` | `comline-runtime` — core runtime only; `std` a feature, not a `core_no-std` fork; `runtime-langs/*` move into their `comline-<lang>` repos; `runtime-std-extra` folds into per-language `std-extra` (or a shared opt-in crate) |
| `cli` | the generator registry pulls a generator crate from each `comline-<lang>` repo behind cargo features; `comline generate` composes them |
| *new* | `comline-<lang>` per target language; a **conformance corpus** (own repo or a `core` dir) that every target must pass |

## Rollout order

Everything is wired by git rev (see the Decision note). Nothing here needs a
big-bang; each step leaves the tree working.

| # | Step | Kind | Notes |
|---|---|---|---|
| 1 | **`generation` → `comline-codegen`**: strip to contract + helpers + `Registry` | code | The `rust` / `typescript` generator bodies come *out* in step 4; what's left is language-neutral. Consumed by git rev. |
| 2 | **[`core ↔ target` contract doc](core-target-contract.md)** ✅ drafted | design doc | Frozen-IR format, IR→types mapping, core-runtime API surface, call-system framing, FFI/ABI. It is a public API across many repos now. |
| 3 | **Conformance corpus** — schema + expected output, standing before the *second* target repo | code | The only thing keeping generators consistent once they don't share a repo. *Codegen half started* — `generation`'s `comline-conformance` crate (hand-built `FrozenUnit` fixtures × every generator, golden-diffed). The runtime half follows once a runtime exists. |
| 4 | **`comline-typescript`** — the pilot target repo | code / infra | *Done.* `ComlineProject/comline-typescript` holds `codegen/` (`comline-codegen-typescript`, extracted from `generation`) and `runtime/` (`@comline/runtime`, MPL-2.0, Node) — so far the framing-agnostic contract + a `Handshake` byte-compatible with `comline-runtime` + a `JsonCodec` (comline-typescript#6). The CLI and the conformance corpus depend on the generator by git rev. `libgen` / the rest of the runtime / `std-extra` land there next; CI runs a cargo job and a Node job. |
| 5 | **`comline-rust`** — generator now; the rust runtime from `runtime-langs/` later | code / infra | *Generator done.* `ComlineProject/comline-rust` holds `codegen/` (`comline-codegen-rust`), extracted from `generation`; the CLI and the conformance corpus depend on it by git rev. `generation` is now just `comline-codegen` + `conformance`. The runtime lift waits for step 7 (and the FFI/dylib G2c). |
| 6 | **CLI feature-gated `Registry`** — compose steps 4–5 behind `--features` | code | *Done.* `comline-codegen-rust` / `-typescript` are optional deps behind `gen-rust` / `gen-typescript` (both default); `generator_registry()` `#[cfg]`-guards each `register()`. `--no-default-features --features gen-rust` drops the other's whole dep tree. |
| 7 | **`runtime` → `comline-runtime` only**; `std` a feature; `runtime-std-extra` opt-in | code | *7a–7e done.* `comline-runtime` is `no_std`-first (`std` an additive feature, not the deleted `core_no-std` fork). **7a** — `src/contract/` holds the surface-4 traits (`RuntimeError`, `BufMut` + `SliceBuf`, `WireFormat`, `Dispatch` + `Kind`, `CallError`, `Envelope`), `no_std` + alloc-free. **7b** — `format::MsgPack` implements `WireFormat` over `rmp-serde` (encodes straight into a `BufMut`). **7c** — `Kind::resolve` + an end-to-end hand-written-protocol `Dispatch` test. **7d** — the all-stubbed `setup/` layer (`async_trait` + `Arc<RwLock>`, against the sync/no-alloc contract) is deleted and replaced by real `wire` (request/response framing), `transport` (a sync `Transport` trait + an `InMemory` mpsc impl + `duplex()`), and `serve` (`Server<D, W>` holding the `Dispatch`, the `WireFormat`, and three reused buffers). Setup-only deps (`eyre`, `async-trait`, `downcast-rs`, `tokio`, `serde_json`, `json-rpc-types`) and the `json_rpc` feature go with it; `package_abi` stays. **7e** — the consumer side: `client::Client<T, W>` (owns transport + format + request-id counter + reused buffers; `call` returns `(Envelope, &W)` under one borrow), plus a `Tcp` `Transport` with `u32`-length-prefixed stream framing. 7f folds JSON-RPC back in as a framing option, then the async layer. The leftover `runtime-langs/*` move into their `comline-<lang>` repos as those land. |
| 8 | **Remaining languages** — `comline-python`, `comline-lua`, `comline-luau`, … each from the template | infra | No change to the others. |

Steps 2–3 are the real prerequisites for a *second* target repo. `generation`'s
G3 in [Generation → G3](generation.md#g3-split-to-per-language-repos) is steps
1 + 4 + 5 + 6 from the codegen side.

**Publishing to crates.io** stays an open call for later. If the coordinated
git-rev bumps across `comline-<lang>` repos get painful, that is the trigger to
revisit — releasing `comline-core` and `comline-codegen` with semver is the fix,
and it slots in without reordering anything here.

## Ownership & packaging

Every target language is its own repo from the start, so there is no
"graduation" — but the packaging rules still hold and matter more:

**Org-owned registry namespaces.** *If and when* a `comline-<lang>` publishes to
an ecosystem registry for end users — a wheel to PyPI, a package to npm, a rock
to LuaRocks, the crate to crates.io — the `ComlineProject` account holds that
name. Maintainers are granted publish rights, not sole ownership. Publishing runs
through CI **trusted publishing (OIDC)**, no long-lived tokens. A maintainer
stepping away never orphans a published package, and the name stays protected.
(This is separate from inter-repo deps, which are git revs — see the Decision.)

**A repo template.** New target = new repo from a template carrying the standard
layout (`codegen/`, `libgen/`, `runtime/`, `std-extra/`, `conformance/`), the CI
skeleton, and the `comline-core` / `comline-codegen` dependency wiring.

## Still applies regardless

Independent of the layout, and unchanged by the reversal:

- **`runtime-std-extra`** is optional functionality — opt-in, never in a core
  build graph.
- **`core_no-std`** — a `std` feature flag on one crate, not a parallel fork.
- **The conformance corpus** and the **`core` ↔ target contract doc** — under
  the phased plan these were "later"; under E they are hard prerequisites for a
  second target repo (Rollout order, steps 2–3).
