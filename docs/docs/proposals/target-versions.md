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
4. **Dialects belong in `config.idp`,** but need their own pass, language by
   language ([Dialects](#dialects)).

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

## Dialects

Rust's edition and TypeScript's `target` and `module` aren't versions: no
order says which is "newer" in the sense a minimum needs.

**Decided: they belong in `config.idp`,** in the entry for the language, where
`= {}` was reserved for options:

```
code_generation = {
    languages = {
        rust#1.75.0 = { edition = "2021" }
    }
}
```

**They need their own pass, language by language,** before anything is
written down. The question is the same as for versions: does a dialect change
only the code, or something a consumer relies on? Some do. TypeScript's
`module` (CommonJS or ESM) decides whether the package can be imported at
all, so a consumer couldn't safely change it. Others may be safe to raise, as
a version is.

## Open questions

- **Dialects, language by language:** which options there are, which change
  only the code, and whether a consumer may change any of them.
- **`comline new`:** recommended to scaffold the floor (`rust#1.70.0`, as
  today). That declares the widest promise, and since consumers can raise but
  never lower, a higher scaffold would shut out older toolchains for good.
  When the floor is too low for something the schema uses, the build's error
  names the version to declare. Not yet decided.
- **How the gap past the ceiling is reported,** and whether a consumer has to
  accept it (as with `accept_unverified`) or only sees it.

## What it touches

- **generation:** `Registry::find` and `Registry::support` by floor, version
  gates on `Support`, boundaries and the verified ceiling, the matrix and
  `features.json`, and conformance at every boundary: goldens that carry
  over, generated code compiled with each boundary's toolchain, and encoding
  compared across boundaries.
- **comline-rust and comline-typescript:** declare boundaries, gate features,
  and compare versions against boundaries in their output.
- **core and cli:** `comline build` checks every declared target and the
  dependencies' declarations, and `comline.toml` may only raise
  `lang_version`. Plus lookup by floor, the new messages, and `comline
  targets`.
- **language-server:** lookup by floor, and the gate messages.
- **docs:** the codegen guide's `lang_version`, the language reference pages,
  and the earlier note in Design → Generation, which points here once this is
  decided.
