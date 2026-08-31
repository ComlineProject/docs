# Proposal A — split by concern

Status: **accepted** — the direction the current
[design record](../../design/runtime-repo-structure.md) follows · Re-examined
against [Proposal B — split by language](split-by-language.md) · See the
[section overview](index.md) for the question both answer.

**Proposal.** Keep `generation` (codegen + libgen) as a single repository for the
long run, and let `runtime` start as one repository that graduates *individual*
heavyweight language runtimes into their own repositories as each earns it. The
two split at the same conceptual seam — a language-agnostic core plus per-language
parts — but on very different timelines, because the two are different kinds of
software.

The org-wide rollout (the phased plan, the options weighed, the graduation
criteria) is the decision record in
[Design → Runtime & generation repository structure](../../design/runtime-repo-structure.md).

## Shape

Two repositories, split at the language-agnostic-core / per-language seam.

**`generation` — one repository, long-term.** `code` generation is string
emission with one dependency (`comline-core`). `lib` / `dylib` generation adds
per-ecosystem manifest templating and, for `dylib`, FFI tooling (`cbindgen`,
`abi_stable`) — medium weight, still far lighter than a runtime binding.

```
generation/
  crates/codegen        comline-codelib-gen — every `code` generator
                        (rust, typescript, python, lua, luau, …); pure string emission
  crates/lib-rust       `lib` / `dylib` for rust — cbindgen, abi_stable      ┐ non-default
  crates/lib-python     `lib` for python — pyproject templating              │ members, pulled
  crates/lib-lua        `lib` for lua — rockspec templating                  │ in by the CLI
  crates/lib-node       `lib` for node — package.json + napi glue            ┘ behind features
```

A root `cargo build` builds `codegen` only; each `lib-*` crate is a non-default
member with its own path-filtered CI job. The generator registry
(`find_generator`) moves into the CLI behind cargo features when the first
`lib-*` crate lands — see
[Design → Generation](../../design/generation.md#generator-crate-layout).

**`runtime` — one repository that sheds weight.** It graduates a language only
when that language needs its own release cadence to an ecosystem registry, or
gets a maintainer outside the core team. Toolchain weight alone is handled
in-repo by non-default members and path-filtered CI.

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
Node, later perhaps Go or Swift) — not one per language.

**The seam.** Generated code imports the runtime. The `lib` generator for
language *X* writes a manifest that depends on **`comline-runtime` for X** at a
compatible version — so `generation` carries, per target language, a small table
of *strings* (the runtime package name and its version range), kept in step with
the `core ↔ runtime` contract. Not a code dependency between the repositories.

```
runtime releases vX
        │
        ▼
core ↔ runtime contract doc:  "IR feature Y requires runtime ≥ vX"
        │
        ▼
lib generator for X emits:    depends on comline-runtime-X  ">= vX"
```

## The case for it

- **It follows the actual fault lines.** Codegen runs at build time inside the
  toolchain; the runtime ships to end users at execution time. Different
  audiences, cadence, security surface — and different dependency weight:

  |  | codegen / libgen — `generation` | runtime — `runtime` |
  |---|---|---|
  | When it runs | build time, in `comline generate` | execution time, in the user's app |
  | Depends on it | the Comline CLI | the *generated code*, as an ecosystem dependency |
  | Shipped to users | no — only its output is | yes — crate / wheel / rock / npm |
  | Weight | light: string emission, manifest templating | heavy: `pyo3`/`napi`/`mlua` want a full native toolchain |

- **The weight is quarantined where it actually is.** A Python *code generator*
  is as light as the existing TypeScript one; a Python *runtime* needs CPython
  headers and multi-platform wheels. Keeping them apart means the toolchain side
  never drags in a language SDK.
- **Minimal repo growth.** Lightweight bindings (c, lua, luau) never leave
  `runtime`; only genuinely heavy languages get their own repo. `generation`
  stays a single repo indefinitely.
- **Independent release cadence** for the two concerns, and for each graduated
  runtime, without a repo-per-language explosion.

## The case against

- **A change that spans both** — a new IR feature that needs generator *and*
  runtime support — touches two repos and the contract doc between them, in
  sequence, rather than one PR.
- **The seam is indirect.** The generator↔runtime agreement is a version range
  in emitted text, mediated by a hand-maintained contract doc and a
  per-language name/version table. Nothing fails to compile if that table drifts
  — only the conformance corpus catches it.
- **"Where does Python live" has two answers** — the generator in `generation`,
  the runtime in `runtime` or `runtime-python`. A contributor working on Python
  support crosses repos.
- **Two conformance surfaces to keep honest** — the corpus lives with the
  runtime, but it is really testing the generator's output too, from across a
  repo boundary.
- **The graduation call is a judgement, not a rule** — "does this language need
  its own repo yet?" gets re-litigated per language.

## When this would be the right call

When build-time tooling and the shipped runtime genuinely have different
audiences and cadence — which they do now — and when most target languages are
lightweight bindings with only one or two heavy outliers. It fits a core team
that owns the toolchain centrally and wants to add languages without standing up
a repo, a release pipeline, and a CI matrix for each. It is the conservative
choice: it defers the per-language split until a specific language's weight and
ownership make it unavoidable.
