# Licensing

Status: **decided** · Supersedes the `MIT OR Apache-2.0` set in
`core@ea8f1e5` / `cli@5d5ae2f` · Affects every `ComlineProject/*` repo

## Decision

| repo(s) | license | why |
|---|---|---|
| `core`, `generation`, `comline-rust`, `comline-typescript`, `cli` | **GPL-3.0-only** | the **toolchain** — the compiler and code generators; everything that links `comline-core` |
| `runtime` (`comline-runtime`) | **MPL-2.0** | linked *into user applications* |
| generated `<namespace>` files | *the user's* — no Comline license attaches | output of a tool is not a derivative of the tool |
| `docs` | **CC-BY-4.0** | prose, not code |
| `brand` | **not open-licensed** — trademark reserved, nominative use granted (`brand/TRADEMARK.md`) | a fork may copy the code; it may not *be* "Comline" |

`GPL-3.0-only`, **not** `-or-later`: adopting a future GPL revision stays a
deliberate act, not automatic delegation to the FSF.

## The goal

A company should be able to fork Comline (that is what open source is) but
**not** take the fork closed and out-compete the original with a proprietary
version. At the same time, building proprietary software *with* Comline must
stay unencumbered, and there is **no** commercial-licensing / open-core plan —
copyleft has to just work, not be a sales lever.

That is exactly what copyleft-on-the-toolchain plus a linking-friendly runtime
delivers. It is the **GCC model**: a copyleft compiler, a runtime you may link
into anything, and output that belongs to whoever ran the tool.

## Why the split falls where it does — the link graph

```
   comline-core ◄────────┬────────── comline-codegen ◄──┬── comline-codegen-rust
   (compiler / library)  │           (neutral contract) └── comline-codegen-typescript
        ▲                │                 ▲    ▲                      ▲
        │                │                 │    │                      │
        └──── comline CLI ─────────────────┘    └──── comline-conformance
               (also links the -rust / -typescript generators)

   ═══════ toolchain (GPL-3.0-only): everything above links comline-core ═══════

   generated <ns>.rs  ──links──►  comline-runtime  (MPL-2.0)
      (the user's)                     └─ deps: serde, bytemuck, abi_stable,
                                          libloading, rmp — no comline-* dep
```

Verified by walking every `[dependencies]` and cross-crate `use`:

- **`comline-runtime` does not depend on `comline-core`** — zero references
  anywhere under `runtime/`. The two halves meet at exactly one edge —
  *generated code → `comline-runtime`* — which points *out of* the toolchain,
  never back in.
- Everything else (`comline-codegen`, `comline-codegen-rust` / `-typescript`,
  `comline-conformance`, the `comline` CLI) links `comline-core`, so all of it
  is GPL — a distributed fork must ship *all* its source under GPL, not just the
  changed files. That is the anti-appropriation guarantee.
- `comline-core`'s own dependencies (`tree-sitter` / `rust-sitter`, `eyre`,
  `snafu`, `chumsky`, `ariadne`, `codespan-reporting`, `handlebars`, `blake3`,
  …) are all permissive (MIT / Apache-2.0 / ISC / CC0) and therefore
  GPL-3.0-compatible — permissive licenses flow *into* GPL.

## What GPL does **not** reach

- **Your application.** Running `comline generate` to produce bindings no more
  licenses your program than compiling it with GCC does. The GPL covers the
  generator's *own* source, not its output.
- **Generated code.** The emitted `<namespace>` files are yours to license as
  you wish. Their only external constraint is `comline-runtime`, which is
  MPL-2.0 and explicitly linking-permissive.
- **`comline-runtime`.** MPL-2.0 — modifications to *its* files must be
  published when you distribute them, but linking it into a closed-source
  application is fine (MPL §3.3). This is the piece that keeps commercial use
  alive.

## Why `-only`, not `-or-later`

`-or-later` lets recipients comply with any future GPL the FSF publishes, and
lets the project ride those revisions without re-collecting contributor
consent. `-only` freezes the terms at v3: a future GPL becomes an explicit
relicensing choice rather than an automatic one. The project is a solo effort
that would rather keep that decision in its own hands than delegate it — the
same reasoning Linux uses for GPLv2-only. Being the sole copyright holder, it
can still opt into a future GPL deliberately if one lands that it likes.

## Open

- **stdlib schemas.** `comline-core-stdlib` sits in the `core` repo and is
  GPL-3.0-only by default. The stdlib *schemas* — things a user writes
  `use std::…` to pull into their own schema — arguably want a permissive /
  CC0 license, the way C standard-library headers carry an exception, so
  incorporating them raises no questions. Decide when validators / `lib`-mode
  stdlib codegen actually lands.
- **generated-file header.** A one-line note in each generated file stating the
  output is not GPL — a small follow-up (it touches the conformance goldens).

## Practical notes

- **Sole copyright holder** (`git shortlog -sne` across every repo shows one
  contributor). No sign-offs were needed to relicense.
- Code already distributed under `MIT OR Apache-2.0` stays usable under those
  terms by anyone who already has it — a licence grant cannot be revoked
  retroactively. Every release from the switch forward is GPL-3.0-only /
  MPL-2.0.
- Contributions are taken under the repo's license (GPL-3.0-only for toolchain
  repos, MPL-2.0 for `runtime`), no CLA.
