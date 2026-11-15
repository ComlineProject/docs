# Ready for 1.0

What must be true before the 1.0 announcement. **Draft,** 2026-10-31, updated 2026-11-16.

From 1.0 the [promises](phases.md#from-the-10-announcement) hold: semver,
deprecation before removal, frozen wire bytes, a frozen C ABI within a major,
and registry publishing. So anything those promises would freeze has to be
right first, and anything they require has to exist.

An item is done when it is merged, documented and proven by conformance where
that applies.

## Wire formats

At 1.0 a format's bytes never change again, so every format that ships as
stable is finished first.

- Known wire bugs in the formats that ship are fixed in every runtime:
    - trailing bytes accepted by `msgpack@1`, the envelope and the handshake
      ([runtime#33](https://github.com/ComlineProject/runtime/issues/33));
    - TypeScript accepting unknown enum variants and out-of-range integers
      ([comline-typescript#57](https://github.com/ComlineProject/comline-typescript/issues/57)).
- Unknown enum variants: decided on 2026-10-20, strict by default with `@open`
  enums as an opt-in, and no silent fallback. What's left is building it: the
  `@open` annotation in core, an `Unknown` case in generated code, and
  refusing an unknown variant in every runtime
  ([runtime#17](https://github.com/ComlineProject/runtime/issues/17)).
- The handshake that ships is final. The compatibility check
  ([runtime#15](https://github.com/ComlineProject/runtime/issues/15)) is
  **built** (2026-11-08).
- `json@1` and `jsonrpc@1` ship as stable, so their known bugs are fixed
  first:
    - [runtime#38](https://github.com/ComlineProject/runtime/issues/38),
      [#40](https://github.com/ComlineProject/runtime/issues/40) (**built**,
      2026-11-07),
      [#58](https://github.com/ComlineProject/runtime/issues/58);
    - [comline-typescript#73](https://github.com/ComlineProject/comline-typescript/issues/73),
      [#74](https://github.com/ComlineProject/comline-typescript/issues/74),
      [#75](https://github.com/ComlineProject/comline-typescript/issues/75)
      (**built**, 2026-11-08);
    - [comline-rust#76](https://github.com/ComlineProject/comline-rust/issues/76).

## Schema language

A schema written for 1.0 keeps building on every 1.x.

- The syntax that would be awkward to add later is settled:
    - tagged unions ([core#126](https://github.com/ComlineProject/core/issues/126));
    - bounds on types ([core#98](https://github.com/ComlineProject/core/issues/98)),
      **built** (2026-11-09);
    - explicit function ids, `@id` ([core#127](https://github.com/ComlineProject/core/issues/127));
    - packet dispatch, if it ships ([core#123](https://github.com/ComlineProject/core/issues/123)).
- Language editions exist, so later syntax changes don't need a major
  ([core#102](https://github.com/ComlineProject/core/issues/102)).
  **Built** (2026-11-09).

## Versions of user packages

Semver for a user's schema package means nothing until a break is defined.

- The compatibility rules are decided and enforced
  ([core#119](https://github.com/ComlineProject/core/issues/119)), applying
  the rules of the encodings a package declares
  ([core#117](https://github.com/ComlineProject/core/issues/117)).
- `comline diff` and `comline build` report every change that matters
  ([cli#80](https://github.com/ComlineProject/cli/issues/80)), and no false
  breaks ([core#110](https://github.com/ComlineProject/core/issues/110),
  **built** 2026-11-01). Both now print own, dependency and config changes and
  the bump. What's left is `--json` output, and failing a build on a break
  through `versioning.allow` and `comline build --deny`.
- `comline release` can make 1.0 and raise or lower a bump with a reason
  ([cli#82](https://github.com/ComlineProject/cli/issues/82)).
  `comline release`, `comline release 1.0` and `--raise` with a reason are
  **built**. What's left is `--lower`, requiring `@id` before 1.0 (it waits on
  [core#127](https://github.com/ComlineProject/core/issues/127)), and showing
  why a bump is what it is in `build` and `diff`.
- Releases carry a changelog
  ([core#7](https://github.com/ComlineProject/core/issues/7)).
  [`comline doc`](../reference/tools/cli/doc.md) generates one between any two
  versions, and the diff now classifies every change kind. **Built**
  (2026-11-15).

## Interfaces that freeze

- The C ABI's structs, status codes and flags are final for 1.x, including
  `comline_connection_size`/`init` and whether a `comline@2` changes the event
  struct ([C ABI](../reference/languages/c-abi.md)).
- The IR and `config.idp` formats are stable, or versioned with a reader for
  every older version
  ([core#146](https://github.com/ComlineProject/core/issues/146), closed as
  not planned: the work moved to the IR migrations track below).
- IR migrations: every stored format migrates accurately and provably, and a
  command never deletes or changes a store on its own. From 1.0 every format
  change is a migration step, with fixtures kept for ever. The framework
  and format 4 come first, then the 1.0 refusal of pre-1.0 stores
  ([core#268](https://github.com/ComlineProject/core/issues/268), design
  [accepted](../proposals/ir-migrations/index.md); the framework is partly
  built).
- The shared vocabulary: one catalog of the names several programs agree on
  (encodings, facts, guarantees, annotations, diagnostic codes), read by core,
  the runtimes and the language server, plus a granular `@unverified`. A
  published wire name never changes
  ([core#219](https://github.com/ComlineProject/core/issues/219), design
  [accepted](../proposals/shared-vocabulary/index.md); the catalog and the
  runtime side are built, core reading it is open).
- Each runtime's public API, and the shape of generated code, are reviewed
  once for anything we'd want to change
  ([runtime#68](https://github.com/ComlineProject/runtime/issues/68)).
- The versioned specifications that tools outside this project rely on are
  reviewed and numbered for 1.0:
    - the [generator protocol](../reference/generator-protocol.md), including
      its render request (version 0 today);
    - encoding profiles and the [conformance](../reference/conformance/index.md)
      corpus and ops protocol;
    - the documentation model behind [`comline doc`](../reference/tools/cli/doc.md)
      (version 1 today);
    - the [`comline.toml` schema](../reference/package/comline-toml.md)
      (`0.x` today);
    - the JSON from [`comline inspect --json`](../reference/tools/cli/inspect.md).
- The extension API is part of 1.0, so it is designed, built and frozen
  first: third-party formats, framings, transports and dispatchers
  ([core#120](https://github.com/ComlineProject/core/issues/120)), and
  generators outside the CLI build
  ([core#8](https://github.com/ComlineProject/core/issues/8)).
  **Built** (2026-11-01). Freezing it is the specifications item above.

## Proof

- Every runtime that ships passes the conformance vectors and the
  differential harness against the Rust reference, driven by
  `comline conformance --impl`
  ([comline-typescript#98](https://github.com/ComlineProject/comline-typescript/issues/98),
  **built** 2026-11-01).
- The compiler has fuzzing, IR round-trip tests and cross-platform CI
  ([core#9](https://github.com/ComlineProject/core/issues/9)). **Built**
  (2026-11-09).
- The benchmark gates hold, with no accepted regression left unexplained.
- Rust and TypeScript ship at 1.0. Other languages follow in 1.x, on the
  shared core.

## Distribution

- Package names are owned by ComlineProject on every registry used (crates.io,
  npm, …) ([docs#102](https://github.com/ComlineProject/docs/issues/102)).
  Partly done: `comline` and `comline-core` are reserved on crates.io, but
  owned by a personal account, not a ComlineProject team. The other crate
  names are not reserved, and the npm `@comline` scope isn't confirmed.
- Publishing runs from CI with trusted publishing (OIDC), no long-lived tokens
  ([cli#1](https://github.com/ComlineProject/cli/issues/1)).
- Builds are reproducible and checksums are published. The TypeScript core's
  `.wasm` already is.
- The runtimes are published, so generated code needs no vendoring:
  `comline-runtime` on crates.io
  ([runtime#115](https://github.com/ComlineProject/runtime/issues/115)),
  `@comline/runtime` on npm
  ([comline-typescript#154](https://github.com/ComlineProject/comline-typescript/issues/154)),
  and generated Rust names a published version
  ([comline-rust#115](https://github.com/ComlineProject/comline-rust/issues/115)).
- Offline and air-gapped use works: an `--offline` switch and `comline fetch`,
  hash-checked dependencies from several sources, mirrors and signed bundles,
  and release artifacts with checksums, signatures and an SBOM. Nothing calls
  home. The runtime publishing above is the part of this track that 1.0
  requires ([core#227](https://github.com/ComlineProject/core/issues/227),
  design [merged](../proposals/offline/index.md); no stage is built yet).
- The hosted package registry ships at 1.0, with its meta information API
  ([package-registry#1](https://github.com/ComlineProject/package-registry/issues/1)).

## Docs and project

- The docs describe 1.0 as it ships: guides, references, feature-support
  tables, and the tutorial and examples.
- The deprecation and changelog process from the
  [promises](phases.md#from-the-10-announcement) is written down
  ([docs#103](https://github.com/ComlineProject/docs/issues/103)). The policy
  is in [From the 1.0 announcement](phases.md#from-the-10-announcement), and
  `comline doc` generates changelogs. What's left is the maintainer-facing
  practice for the Comline repositories themselves.
- Each repository has a licence, a security policy saying how to report a
  vulnerability, and contributing notes
  ([docs#101](https://github.com/ComlineProject/docs/issues/101)). The
  org-wide `SECURITY.md` covers the security policy. The licence, missing in
  11 repositories, is tracked in
  [.github#5](https://github.com/ComlineProject/.github/issues/5). Only
  runtime has contributing notes.
