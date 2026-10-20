# Language target versions

Status: **under discussion** · tracked in
[generation#76](https://github.com/ComlineProject/generation/issues/76) ·
partly decided (see [Decided](#decided)), nothing implemented

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

## Decided

With the user, 2026-10-20:

1. **`config.idp` sets the version,** and the build proves it
   ([The declaration is a promise](#the-declaration-is-a-promise)).
2. **`comline.toml` may only raise it, never lower it,** and only because a
   version never changes the wire
   ([Raising the version](#raising-the-version)).
3. **Generators have upper bounds,** for the sake of the guarantee: a verified
   range, with going past it marked the way `@unverified` marks other gaps
   ([Upper bounds](#upper-bounds-a-verified-range)).
4. **Dialects belong in `config.idp`,** but a generator removes a dialect
   before making it an option: it emits code valid under every setting it
   supports, and offers an option only where no single output fits. For Rust
   and TypeScript that leaves none ([Dialects](#dialects)).
5. **`comline new` scaffolds the floor** (`rust#1.70.0`, as today). That
   declares the widest promise; since consumers can raise but never lower, a
   higher scaffold would shut out older toolchains for good. When the floor is
   too low for something the schema uses, the build's error names the version
   to declare.

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

## The declaration is a promise

Today a declared target promises nothing. Only `comline generate` checks
features, and only for the target it's generating. `comline build` never
looks at `code_generation.languages`, so a package can declare `rust#1.70.0`
and use a feature the Rust generator only supports from 1.75.

**`comline build` checks every declared target.** Each feature the schema
uses must be supported at the declared version, or the build fails, naming
the feature and the version that would support it. Then `rust#1.70.0` means
"this package is proven to generate for Rust 1.70 and later", and consumers
can rely on it.

**Dependencies:** a dependency declaring `rust#1.75.0` can't be generated
into a package built for 1.70. A target's version is at least the highest
among the package's own declaration and its dependencies' declarations for
that language, or the build refuses and names the dependency.

## Raising the version

A consumer's `comline.toml` can set `lang_version` for one target:

- **Higher than declared:** allowed. Anything that builds on 1.70 builds on
  1.75, so the promise holds, and it unlocks options the author didn't need.
  For example, `async = true` needs 1.75 without the author having to change
  `config.idp`.
- **Lower than declared:** an error naming the declared minimum. It would go
  below what the author proved.

**This rests on one rule: a version changes the generated code, never the
wire.** Code generated at 1.70 and at 1.75 must encode and decode
identically, or two peers on different toolchains could disagree while their
handshake (which hashes the IR, not the code) still matches. Conformance
proves it: at every boundary, the generated types encode alike.

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

## Upper bounds: a verified range

Whether a newer toolchain still builds the output depends on the language:

- **Rust** promises that newer compilers build older code, editions aside.
- **TypeScript doesn't:** releases change type-checking, so code proven against
  5.x may not type-check on 6.0.

So **a generator declares the range it has verified:** its floor, and a
ceiling at the newest toolchain its output has been compiled against.
Conformance then has to **compile** the generated code with the toolchain at
each boundary and at the ceiling, not only compare it with goldens.

**Past the ceiling, the target is unverified, not refused.** It works the way
[`@unverified`](../guide/idl/protocol.md#giving-up-a-guarantee) does: allowed,
with the gap stated in build output and reported, never silently assumed. A
hard error would break every package the day a compiler releases. For a
language that promises forward compatibility, the generator can say so, and
the ceiling only bounds the dialects (Rust's editions).

### Reporting the gap

*Proposed, not yet decided.* Two cases, because comline knows the declared
version but never the compiler a consumer actually runs:

**1. A declared or raised version above the ceiling** (`rust#1.95.0` when the
generator has verified up to 1.90):

- **It generates as the newest boundary,** and the build and `comline
  generate` warn under their own diagnostic code,
  `generation::unverified-version`. Like the `unverified::*` codes, a package's
  settings can raise it to an error, so CI can insist on verified targets.
- **The editor warns on the declaration** in `config.idp`. `comline targets`
  shows each generator's ceiling.
- **No acceptance step.** `accept_unverified` exists because a dependency's
  gap reaches its consumers' peers over the wire. This gap doesn't touch the
  wire; it only concerns whoever compiles the code, and that's who sees the
  warning. A dependency's declaration past the ceiling raises a consumer's
  version (see [The declaration is a promise](#the-declaration-is-a-promise)),
  and the consumer's build warns the same way.

**2. A newer compiler than the ceiling:** comline can't see it, so it states
the range where a consumer will look:

- **Every generated file's header names the verified range:** "generated for
  Rust 1.70.0 or later, verified up to 1.90.0".
- **Lib mode records it in the package's own metadata,** where that ecosystem
  checks it. Cargo's `rust-version` already carries the floor, and Rust needs
  no ceiling. A TypeScript package lists `typescript` as a peer dependency at
  `>=` the floor only: a ceiling there would make npm refuse to install the
  package on a newer compiler, which is the hard failure this proposal avoids.

## Dialects

Rust's edition and TypeScript's `target` and `module` aren't versions: no
order says which is "newer" in the sense a minimum needs.

No dialect touches the wire. What one can affect is whether the generated
code builds where it lands:

- **Code mode:** the generated source compiles inside the consumer's own
  project, under its edition, `tsconfig` and flags.
- **Lib mode:** the generator emits a package others depend on, whose shape
  (module format, Cargo features) dependents rely on, as they do on its
  version.

**Decided: remove a dialect before configuring it.** A generator emits code
valid under every setting it supports, and offers an option only where no
single output fits. Such options go in the `config.idp` entry for the
language, where `= {}` was reserved for them: C's
`std = "c11"`, say, since `-std=c89` and `c11` change what can be written at
all. For Rust and TypeScript the pass below finds
none.

### Rust

| Axis | Today | Decided |
|---|---|---|
| **Edition** | Lib mode writes `edition = "2021"`; code-mode source compiles under the consumer's edition | Crates of different editions work together, so dependents never see a package's. In code mode only keywords differ (`async`, `dyn`, `try` from 2018; `gen` from 2024), and the generator doesn't escape any, so a field named `gen` breaks inside a 2024 crate. **Escape every edition's keywords with `r#`.** Lib mode's edition follows from the version: 2024 from 1.85, otherwise 2021. |
| **`std` / `alloc` / `no_std`** | The runtime supports all three | The consumer's environment decides, not the author. **Lib mode exposes them as Cargo features,** chosen when building. |
| **`async`** | A per-target `comline.toml` option ([runtime#19](https://github.com/ComlineProject/runtime/issues/19)) | **Stays a `comline.toml` option, in both modes.** It only matters for a generated package published for others to depend on, whose publisher would choose for every dependent; a Cargo feature would let each choose. The only such package today, `comline_std`, has no connection protocols, so this is revisited if one appears. |

### TypeScript

| Axis | Today | Decided |
|---|---|---|
| **`target`** (ES level) | Lib mode fixes ES2022; the output uses `bigint`, which needs ES2020 | **No option.** The generator states ES2020 as a requirement, shown by `comline targets`. |
| **`module`** | Lib mode emits ESM (`"type": "module"`, NodeNext), with `.js` extensions in imports | That works under NodeNext and bundler resolution, and Node 22 can `require()` ESM. **ESM only,** unless a CommonJS-only consumer appears. |
| **Erasable syntax** | `export enum`, and constructor parameter properties (`constructor(private readonly impl …)`) | Neither works under TypeScript 5.8's `erasableSyntaxOnly` or Node's built-in type stripping. **Emit a `const` object and a union type instead of an enum, and plain fields.** `Color.Red` still works; the enum's type changes shape. |
| **Strict flags** | `import type` already used | **Conformance type-checks the output under the strictest set** (`exactOptionalPropertyTypes`, `noUncheckedIndexedAccess`, `verbatimModuleSyntax`), so it builds under any. |

## Open questions

- **[Reporting the gap](#reporting-the-gap)** past the ceiling, as proposed
  there: a warning code that settings can raise, no acceptance step, and the
  verified range stated in generated headers and package metadata.

## What it touches

- **generation:** `Registry::find` and `Registry::support` by floor, version
  gates on `Support`, boundaries and the verified ceiling, the matrix and
  `features.json`, and conformance at every boundary: goldens that carry
  over, generated code compiled with each boundary's toolchain, and encoding
  compared across boundaries.
- **comline-rust and comline-typescript:** declare boundaries, gate features,
  and compare versions against boundaries in their output. Rust escapes every
  edition's keywords, derives lib mode's edition, and exposes `std` / `alloc`
  as Cargo features. TypeScript emits enums as `const` objects with union
  types, drops parameter properties, and is type-checked under the strictest
  flags.
- **core and cli:** `comline build` checks every declared target and the
  dependencies' declarations, and `comline.toml` may only raise
  `lang_version`. Plus lookup by floor, the new messages, and `comline
  targets`.
- **language-server:** lookup by floor, and the gate messages.
- **docs:** the codegen guide's `lang_version`, the language reference pages,
  and the earlier note in Design → Generation, which points here once this is
  decided.
