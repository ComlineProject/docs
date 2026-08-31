# Runtime & generation repository structure

Status: **decided — phased** (C-light now · contract + releases next · B
per-language as earned; D/E rejected, F is the end state) · Affects
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

`ComlineProject/generation` faces the mirror of this on the codegen side. The
de-rot settled it at the `code` / `lib` boundary — every language's `code`
generator in one crate (`comline-codelib-gen`), one crate per language for
`lib` / `dylib` where the heavy deps (`pyo3`, `mlua`, `cbindgen`, `abi_stable`)
live, and the registry moving to the CLI behind cargo features when the first
per-language `lib` crate lands. See
[Generation → Generator crate layout](generation.md#generator-crate-layout).

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

The six layouts weighed before landing on the phased path in the Decision
section below. The chosen route threads **C** (now) → **B** (per language, as
earned), with **F** as the end state.

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

## Decision — phased, not big-bang

Adopt the phased path below. **D and E are rejected** — they relocate the
weight and couple lifecycles that must stay apart (build-time tooling vs a
shipped runtime). **F is the intended end state**, but only after step 2's
contract doc exists and has held stable across a release or two.

### Step 1 — now, in the existing `runtime` repo (Option C, lightly)

Near-zero migration, takes most of the pain out:

- every `runtime-langs/*` becomes a **non-default workspace member** — a root
  `cargo build` / `cargo test` builds the core runtime only;
- **CI splits into path-filtered per-language jobs** — a Python PR never
  installs the Lua toolchain, and vice versa;
- **`runtime-std-extra` moves to its own opt-in crate**, out of the core
  runtime's build graph;
- **`core_no-std` collapses into a `std` feature** on `comline-runtime` — one
  crate with a feature flag, not a parallel fork.

### Step 2 — before the 2nd or 3rd language gets real

- Write the **`core` ↔ runtime contract** as a design doc: the frozen-IR
  format, the frozen-IR-to-types mapping, the core-runtime API surface, the
  call-system framing, the FFI/ABI. This doc is the single thing that decides
  whether any multi-repo split is tolerable.
- Start **semver-releasing `comline-runtime`** to crates.io so bindings depend
  on a version, not a path. Do the same for `comline-core` /
  `comline-codelib-gen` on the generation side — it ends the git-rev pinning
  that currently couples `generation` and `cli` to `core` commit hashes.
- Stand up a **language-agnostic conformance corpus** — schema + expected
  behaviour every runtime must pass. It matters more the more the tree splits.

### Step 3 — graduate one language at a time (Option B, incrementally)

When a binding meets the criteria below, move *that one* to its own repo
(`runtime-python`, `runtime-node`, …) depending on a released `comline-runtime`
and owning its ecosystem packaging. Light bindings stay in the mono-repo. The
tree settles into a hybrid: `runtime` (core + lightweight bindings) plus a
handful of graduated per-language repos.

For `generation`'s side, [Generator crate layout](generation.md#generator-crate-layout)
takes the same line: `code` generators stay together, `lib` / `dylib` go
per-language.

## Graduation criteria & ownership

**What triggers step 3 for a binding.** It stays in the mono-repo as long as
non-default members + path-filtered CI keep it cheap for everyone else.
Toolchain weight or CI minutes **alone are not a trigger** — that is exactly
what step 1 handles. A binding graduates to its own repo when **either**:

- it must **publish to an ecosystem registry** (PyPI / npm / LuaRocks) on a
  cadence independent of `core` releases — the point where "one tag ships
  everything" actually breaks; **or**
- a **maintainer outside the core team owns it** end to end.

On current shape, expect **Python** and **Node** to clear the bar; `mlua` /
`luau` bindings likely will not.

**Who owns the packaging.** For any graduated language the registry namespace
is **org-owned** — the `ComlineProject` account holds the PyPI project / npm
scope / LuaRocks module; maintainers are granted publish rights, not sole
ownership. Publishing runs through CI **trusted publishing (OIDC)**, no
long-lived tokens. A maintainer stepping away never orphans a published
package, and the name stays protected.

`generation` vs `core` for codegen is **resolved** in [Generation](generation.md):
the generators move to `generation`, `core` ships none, and there is no
`comline-core-ir` carve-out.
