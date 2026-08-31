# Per-language target repositories

Status: **under discussion** · Alternative to
[Runtime & codegen repositories](runtime-and-codegen-repos.md) (the direction the
current [design record](../design/runtime-repo-structure.md) follows) · This is
Option **E** from that record, written up in full.

**Proposal.** One repository per target language — `comline-python`,
`comline-lua`, `comline-node`, … — each holding *that language's entire surface*:
its code generator, its library generator, and its runtime, plus any
language-specific standard-library extras. `core` stays language-agnostic;
`generation` shrinks to a shared codegen support crate (or disappears into one).

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

`core` (language-agnostic IR + compiler) and a shared `comline-codegen` support
crate — the `GenRequest` / `GeneratedFile` contract and AST-walk helpers — are
the only things every target repo depends on.

## The case for it

- **The codegen ↔ runtime contract becomes a same-repo invariant.** Generated
  code has to match what the runtime expects at the FFI boundary. Here that
  agreement is checked in one CI run, in one repo, on every PR — no cross-repo
  version dance, no "which runtime version does this generator target" table.
- **One place per language.** A contributor adding or fixing "Python support"
  works in `comline-python` and nowhere else. Ownership is obvious.
- **Native tooling end to end.** The repo is already a Python repo — its CI has
  CPython, `maturin`, `pytest`; the libgen tests can actually build and import
  the wheel they generate.
- **New language = new repo from a template**, with zero impact on any other
  target. No shared workspace to destabilise, no non-default-member juggling.
- **Independent everything** — versioning, cadence, issue tracker, release
  automation, even licence where an ecosystem demands it.

## The case against

- **It conflates build-time tooling with a shipped dependency.** The code
  generator runs inside the Comline toolchain on a developer's machine; the
  runtime ships to end users. Different audiences, cadence, and security surface
  — bundled here because they share a language, not a lifecycle.
- **The repo is bilingual with mismatched toolchains.** The Python `code`
  generator is light Rust that emits strings; sitting it next to `pyo3` and a
  CPython build makes CI carry both for changes that touch only one.
- **Shared codegen infra fragments.** Every target repo depends on
  `comline-codegen` (or vendors it). A change to the `GeneratedFile` contract is
  now an N-repo rollout — the cross-repo problem this layout claims to avoid,
  moved from the runtime seam to the codegen seam.
- **The CLI depends on N generator crates from N repos.** The `find_generator`
  registry pulls a crate from each target repo; a release of any target can move
  the CLI's lockfile.
- **Cross-language consistency still needs a shared suite.** "Do the Rust and
  Python generators treat an optional field the same way?" is only answerable by
  a corpus spanning targets, which no single target repo owns.
- **Heaviest coordination for `core` changes.** An IR change touches every target
  repo; the `core` ↔ target contract becomes a public API across many repos.

## When this would be the right call

If Comline reaches a point where each supported language has its own dedicated
maintainer or team, ecosystem-native distribution is mandatory across the board,
and the `core` ↔ target contract is stable enough to be a real versioned API,
then per-language target repos stop being overhead and become the natural unit of
ownership. That is the same end state
[Runtime & codegen repositories](runtime-and-codegen-repos.md) tends toward for
runtimes — this proposal applies it to the whole per-language surface, sooner,
and to codegen as well.
