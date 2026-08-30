# Runtime & generation repository structure

Status: **discussion** — no decision, no issues filed · Affects
`ComlineProject/runtime` and `ComlineProject/generation`

The `generation` side — what codegen / libgen / runtime each mean, where the
generators live, and how to clean the repo up — is settled separately in
[Generation](generation.md). This page is about repo granularity for the
*runtime* tree.

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

`ComlineProject/generation` has the same shape for `lib-gen/*`
(`c, lua, luau, python, typescript`), and codegen is split between
`core/core/src/codelib_gen/` (the live `rust` generator) and `generation`'s
`code-gen/*` (commented out) — so *where target code for language X lives* is
already unsettled.

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

## Options

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

## Cross-cutting — independent of A–F

- **`runtime-std-extra` → its own opt-in crate / package**, whatever the layout.
  It is optional functionality; it should not be in the core runtime's build.
- **`core_no-std`** — prefer `std` as a feature flag on one crate over a
  parallel `core_no-std` crate; features scale, a fork does not.
- **Path-filtered, per-language CI jobs** in whichever repo — removes most of the
  "heavy" with no repo move.
- **A versioned `core` ↔ runtime contract doc** — the frozen-IR format, the
  core-runtime API, the call-system framing. This is the single thing that
  decides whether any multi-repo split is tolerable.
- **A language-agnostic conformance corpus** — schema + expected behaviour that
  every runtime must pass. Matters more the more the tree is split.

## Recommendation — phased, not big-bang

1. **Now.** In the existing `runtime` repo: make every `runtime-langs/*` a
   non-default workspace member, split CI into path-filtered per-language jobs,
   extract `runtime-std-extra`. Most of the pain, near-zero migration. This is
   Option **C** applied lightly.
2. **Before the 2nd or 3rd language gets real.** Write the core-runtime +
   call-system + IR-mapping **contract** as a design doc, and start
   semver-releasing `comline-runtime` to crates.io so bindings depend on a
   version, not a path.
3. **When a specific language earns it** — its own maintainer, its own cadence,
   a heavy native toolchain (Python, Node) — graduate *that one* to its own repo
   (Option **B**, incrementally). Light bindings stay in the mono-repo. The tree
   settles into a natural hybrid: `runtime` (core + lightweight bindings) plus
   `runtime-python`, `runtime-node`, … as each earns it.

Avoid **D** and **E** — they relocate the weight and couple lifecycles that
should stay apart (build-time tooling vs shipped runtime). **F** is the right
long-term end state, but only once the contract doc from step 2 exists. The same
playbook applies to `generation/lib-gen/*`.

## Open questions

- **Trigger for step 3.** What concretely promotes a binding to its own repo — a
  named maintainer, a release-cadence divergence, CI minutes, toolchain weight?
- **Org vs ecosystem ownership.** For a language whose runtime graduates, does
  the packaging (PyPI/npm/LuaRocks account) sit with the org or with a
  maintainer?

`generation` vs `core` for codegen is **resolved** in [Generation](generation.md):
the generators move to `generation`, `core` ships none, and there is no
`comline-core-ir` carve-out.
