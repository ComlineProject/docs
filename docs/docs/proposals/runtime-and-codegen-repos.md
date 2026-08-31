# Runtime & codegen repositories

**Proposal.** Keep `generation` (codegen + libgen) as a single repository for the
long run, and let `runtime` start as one repository that graduates *individual*
heavyweight language runtimes into their own repositories as each earns it. The
two split at the same conceptual seam — a language-agnostic core plus per-language
parts — but on very different timelines, because the two are different kinds of
software.

The org-wide rollout (the phased plan, the options weighed, the graduation
criteria) is the decision record in
[Design → Runtime & generation repository structure](../design/runtime-repo-structure.md).
This page states and demonstrates the shape those two repositories take.

## Why they are treated differently

|  | codegen / libgen — `generation` | runtime — `runtime` |
|---|---|---|
| **When it runs** | build time, on the developer's machine or CI, inside `comline generate` | execution time, inside the end user's application |
| **Who depends on it** | the Comline CLI — it is a plugin to the toolchain | the *generated code*, as an ordinary dependency in the target ecosystem |
| **Shipped to users?** | no — only its output is | yes — as a crate / wheel / rock / npm package |
| **Language** | always Rust (it emits strings) | Rust core + language-specific native glue |
| **Dependency weight** | light: `code` gen is string building, `lib` gen is manifest templating | heavy: `pyo3` wants CPython, `napi` wants Node, `mlua` wants Lua headers |

The native-toolchain weight that makes a single workspace painful sits almost
entirely on the **runtime** side. A Python *code generator* is as light as the
TypeScript one that already exists. A Python *runtime* needs CPython headers and
ships wheels for several interpreter versions across several platforms, on its own
schedule.

## `generation` — one repository

`code` generation is string emission with one dependency (`comline-core`).
`lib` / `dylib` generation adds per-ecosystem manifest templating and, for
`dylib`, FFI tooling (`cbindgen`, `abi_stable`) — medium weight, still far lighter
than a runtime binding. So `generation` stays consolidated:

```
generation/
  crates/codegen        comline-codelib-gen — every `code` generator
                        (rust, typescript, python, lua, luau, …); pure string emission
  crates/lib-rust       `lib` / `dylib` for rust — cbindgen, abi_stable      ┐ non-default
  crates/lib-python     `lib` for python — pyproject templating              │ members, pulled
  crates/lib-lua        `lib` for lua — rockspec templating                  │ in by the CLI
  crates/lib-node       `lib` for node — package.json + napi glue            ┘ behind features
```

- A root `cargo build` builds `codegen` only. Each `lib-*` crate is a non-default
  member with its own path-filtered CI job.
- The generator registry (`find_generator`) moves into the CLI behind cargo
  features when the first `lib-*` crate lands — see
  [Design → Generation](../design/generation.md#generator-crate-layout).
- `generation` splitting into per-language *repositories* is out of scope: it
  only makes sense if a generator itself becomes heavy, which is not expected.

## `runtime` — one repository that sheds weight

The runtime starts as one repository and graduates a language only when that
language needs its own release cadence to an ecosystem registry, or gets a
maintainer outside the core team. Toolchain weight alone is handled in-repo by
non-default members and path-filtered CI.

```
Now → Step 1 (in place, one repo):
runtime/
  crates/runtime        comline-runtime — `std` is a feature; the core_no-std fork is gone
  crates/std-extra      comline-runtime-std-extra — opt-in, out of the core build graph
  langs/c  langs/lua  langs/luau  langs/python
                        non-default members; one path-filtered CI job per language
  conformance/          schema + expected-behaviour corpus every runtime must pass

End state:
runtime/                comline-runtime + the light bindings (c, lua, luau)
runtime-python/         graduated — pyo3, PyPI wheels, independent cadence
runtime-node/           napi, npm (born graduated)
runtime-<lang>/         … as each earns it
```

The org grows by roughly **one repository per heavyweight language** (Python,
Node, later perhaps Go or Swift) — not one per language. Lightweight bindings
never leave `runtime`.

## The seam between the two

Generated code imports the runtime. The `lib` generator for language *X* writes a
manifest (`Cargo.toml`, `pyproject.toml`, `.rockspec`, `package.json`) that
depends on **`comline-runtime` for X** at a compatible version. So `generation`
needs, per target language, a small table of *strings* — the runtime package's
name and its compatible version range. That is data kept in step with the
`core ↔ runtime` contract, not a code dependency between the repositories.

```
runtime releases vX
        │
        ▼
core ↔ runtime contract doc:  "IR feature Y requires runtime ≥ vX"
        │
        ▼
lib generator for X emits:    depends on comline-runtime-X  ">= vX"
```

Because the coupling is a version range in emitted text, `generation` and
`runtime` (and any graduated `runtime-<lang>`) release independently. Neither
repository builds or tests the other; the conformance corpus is what proves a
runtime and its generated bindings still agree.
