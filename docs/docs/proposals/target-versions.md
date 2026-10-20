# Language target versions

Status: **under discussion** · tracked in
[generation#76](https://github.com/ComlineProject/generation/issues/76) ·
nothing here is implemented

**The question:** what the version in `rust#1.70.0` means, how it picks a
generator, and how a generator's output and feature support depend on it.
Async connections raised it: their generated Rust uses `async fn` in traits,
which needs Rust 1.75, and no target can say "1.75" today.

## Where things stand

- **A package declares its targets** in `config.idp`, as
  `code_generation.languages = { rust#1.70.0 = {} }`. A consumer's
  `comline.toml` can override the version per target (`lang_version`).
- **The version is looked up as an exact string.** `Registry::find(name,
  version)` in generation's `codegen/src/lib.rs` keys on it, and each
  generator registers one version: `rust#1.70.0` and `typescript#5.0`.
  `rust#1.75.0`, or even `rust#1.70`, finds nothing.
- **The message for that is wrong.** `comline generate` says "this build of
  comline has no rust generator", when it has one at another version.
- **The editor goes quiet.** The language server shows no feature warnings for
  a declared language without an exact match
  (`src/analysis/generation.rs`).
- **The version barely changes output.**
  - Rust writes it into the generated `Cargo.toml` as `rust-version`, and
    nothing else.
  - TypeScript ignores it, and always writes `"target": "ES2022"` into
    `tsconfig.json`.
- **Support is one table per generator.** Each generator has one `SUPPORT`
  table. Conformance runs every fixture at that one version. `FEATURES.md`,
  the [docs matrix](../reference/languages/index.md), `comline targets
  --features` and the editor's warnings all show one column per language.
- **Output that depends on the version already exists:**
  - Generated Rust errors don't implement `core::error::Error`, which is only
    stable from 1.81.
  - Async connection code needs 1.75.
- **An earlier note in [Design → Generation](../design/generation.md#language-version-dialect)**
  proposed one generator per language, with the version and the dialect
  (Rust's edition, TypeScript's `target` and `module`) as that generator's
  configuration. It reserved `= {}` in `config.idp` for those options. This
  proposal builds on it.

## What a version means

| | Meaning | Like |
|---|---|---|
| **A. A minimum** (recommended) | The oldest toolchain the generated code must build on. Newer toolchains build it too. | Cargo's `rust-version`, npm's `engines` |
| B. An exact toolchain | Output for exactly that release | — |
| C. The generator's version | Which generator release made it | — |

A is what the version already does in the generated `Cargo.toml`, and it's
the question a consumer is answering: "what's the oldest compiler my users
have?" Raising it unlocks newer constructs, and lowering it gives them up.

**Comparison:** dotted numbers compared numerically, with missing parts as
zero, so `1.70` is `1.70.0` and `5.0` is `5.0.0`.

## Choosing a generator

**Recommended: a registered version is a floor.** A declared version gets the
generator with the newest floor at or below it, which then receives the
declared version in its request:

- `rust#1.75.0` and `rust#1.82.0` use the generator registered at `1.70.0`,
  told `1.75.0` and `1.82.0`.
- `rust#1.60.0` is an error: "the Rust generator needs `rust#1.70.0` or
  later".
- A rewritten generator could later register at a higher floor beside the old
  one, without breaking packages that declare less.

With one generator per language, as the earlier note proposed, this behaves
the same today. Floors keep the "too old" error expressible.

## Support by version

A feature can be supported from some version on. Options:

| | How | Trade-off |
|---|---|---|
| **A. Version gates on table entries** (recommended) | `(Feature::Async, Support::supported().from("1.75.0", "async fn in traits"))`. Below the gate the feature is unsupported, and the note names the version to declare. | Declarative, so every tool can render and explain it. One column per language stays. |
| B. A table per registered version | Register `1.75.0` beside `1.70.0` with its own table | A second column everywhere that differs in a row or two |
| C. A function of the version | `support(version) -> SupportTable` | Can't be rendered without picking versions to call it at |

Output can also change with the version without any feature's support
changing, as with `core::error::Error` at 1.81. That's the generator's own
business, but it still has to be proven: see the next section.

## Boundaries and conformance

**A generator declares its boundaries:** every version where its support or
output changes. For Rust that would be `["1.70.0", "1.75.0", "1.81.0"]`.

- **Gates name a boundary.** A gate at a version the generator didn't declare
  fails conformance.
- **Output only changes at a boundary.** The generator compares the requested
  version against its boundaries and nothing else, so testing at each boundary
  covers every version.
- **Conformance runs every fixture at every boundary.**
  - A support claim is proven at each one: refused below its gate, matching
    its golden at and above it.
  - **A golden is stored per boundary only where it differs** from the
    previous boundary's; otherwise it carries over. The goldens stay small,
    and a diff shows exactly what a version changes.

## What each tool shows

- **`comline generate`:**
  - A version below the floor says so, naming the floor.
  - A gated feature says what to declare: "async needs `rust#1.75.0` or
    later; this target declares `rust#1.70.0`".
  - The misleading "no generator" message goes.
- **`comline targets`:** `rust ≥ 1.70.0 (changes at 1.75.0, 1.81.0)`.
  `--features` shows each gate.
- **The editor:** warnings at the declared version. Hovering a declared
  `rust#1.70.0` can list what a higher version would add.
- **The docs matrix and `features.json`:** one column per language, with a cell
  like "✅ supported from 1.75.0 (❌ below: async fn in traits)".

## First users

- **`async`** ([runtime#19](https://github.com/ComlineProject/runtime/issues/19)):
  async handlers and senders for connection protocols, supported from Rust
  1.75.0. It's waiting on this proposal.
- **`core::error::Error`** for generated Rust errors, from 1.81.0.
- **TypeScript** has no gates yet, but the same mechanism fits it (`satisfies`
  from 4.9, `const` type parameters from 5.0).

## Dialects

Rust's edition and TypeScript's `target` and `module` aren't versions: no
order says which is "newer" in the sense a minimum needs. They stay generator
options, as the earlier note proposed. **Where they're set is open** (see
below). This proposal only settles versions.

## Open questions

- **Who sets the version?** `config.idp` declares it and `comline.toml`'s
  `lang_version` overrides it. If the declaration means "this package can be
  generated for Rust from 1.70", should a consumer be able to go lower? Or only
  higher? Or should the declaration lose its version and keep just the
  language?
- **Where do dialect options live?** In the `config.idp` entry
  (`rust#1.75.0 = { edition = "2021" }`), where `= {}` was reserved for them,
  or in `comline.toml`, since they don't change the contract?
- **Upper bounds:** a version newer than every boundary is treated as the
  newest one. Is there a case for a maximum, such as a construct a later
  release removed?
- **`comline new`:** scaffold the floor (`rust#1.70.0`, as today) or the newest
  boundary?

## What it touches

- **generation:** `Registry::find` and `Registry::support` by floor, version
  gates on `Support`, boundaries, the matrix and `features.json`, and
  conformance at every boundary with goldens that carry over.
- **comline-rust and comline-typescript:** declare boundaries, gate features,
  and compare versions against boundaries in their output.
- **cli:** lookup by floor, the new messages, and `comline targets`.
- **language-server:** lookup by floor, and the gate messages.
- **docs:** the codegen guide's `lang_version`, the language reference pages,
  and the earlier note in Design → Generation, which points here once this is
  decided.
