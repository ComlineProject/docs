# Ready for 1.0

What must be true before the 1.0 announcement. **Draft,** 2026-10-31.

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
- Unknown enum variants are decided: refused or tolerated
  ([runtime#17](https://github.com/ComlineProject/runtime/issues/17)).
- The handshake that ships is final. If the compatibility check
  ([runtime#15](https://github.com/ComlineProject/runtime/issues/15)) changes
  `comline@1`'s bytes, it lands first, or becomes `comline@2`.
- `json@1` and `jsonrpc@1` ship as stable, so their known bugs are fixed
  first:
    - [runtime#38](https://github.com/ComlineProject/runtime/issues/38),
      [#40](https://github.com/ComlineProject/runtime/issues/40),
      [#58](https://github.com/ComlineProject/runtime/issues/58);
    - [comline-typescript#73](https://github.com/ComlineProject/comline-typescript/issues/73),
      [#74](https://github.com/ComlineProject/comline-typescript/issues/74),
      [#75](https://github.com/ComlineProject/comline-typescript/issues/75);
    - [comline-rust#76](https://github.com/ComlineProject/comline-rust/issues/76).

## Schema language

A schema written for 1.0 keeps building on every 1.x.

- The syntax that would be awkward to add later is settled:
    - tagged unions ([core#126](https://github.com/ComlineProject/core/issues/126));
    - bounds on types ([core#98](https://github.com/ComlineProject/core/issues/98));
    - explicit function ids, `@id` ([core#127](https://github.com/ComlineProject/core/issues/127));
    - packet dispatch, if it ships ([core#123](https://github.com/ComlineProject/core/issues/123)).
- Language editions exist, so later syntax changes don't need a major
  ([core#102](https://github.com/ComlineProject/core/issues/102)).

## Versions of user packages

Semver for a user's schema package means nothing until a break is defined.

- The compatibility rules are decided and enforced
  ([core#119](https://github.com/ComlineProject/core/issues/119)).
- `comline diff` and `comline build` report every change that matters
  ([cli#80](https://github.com/ComlineProject/cli/issues/80)), and no false
  breaks ([core#110](https://github.com/ComlineProject/core/issues/110)).
- `comline release` can make 1.0 and raise or lower a bump with a reason
  ([cli#82](https://github.com/ComlineProject/cli/issues/82)).
- Releases carry a changelog
  ([core#7](https://github.com/ComlineProject/core/issues/7)).

## Interfaces that freeze

- The C ABI's structs, status codes and flags are final for 1.x, including
  `comline_connection_size`/`init` and whether a `comline@2` changes the event
  struct ([C ABI](../reference/c-abi.md)).
- The IR and `config.idp` formats are stable, or versioned with a reader for
  every older version.
- Each runtime's public API, and the shape of generated code, are reviewed
  once for anything we'd want to change.
- The extension API is part of 1.0, so it is designed, built and frozen
  first: third-party formats, framings, transports and dispatchers
  ([core#120](https://github.com/ComlineProject/core/issues/120)), and
  generators outside the CLI build
  ([core#8](https://github.com/ComlineProject/core/issues/8)).

## Proof

- Every runtime that ships passes the conformance vectors and the
  differential harness against the Rust reference.
- The compiler has fuzzing, IR round-trip tests and cross-platform CI
  ([core#9](https://github.com/ComlineProject/core/issues/9)).
- The benchmark gates hold, with no accepted regression left unexplained.
- Rust and TypeScript ship at 1.0. Other languages follow in 1.x, on the
  shared core.

## Distribution

- Package names are owned by ComlineProject on every registry used (crates.io,
  npm, …).
- Publishing runs from CI with trusted publishing (OIDC), no long-lived tokens
  ([cli#1](https://github.com/ComlineProject/cli/issues/1)).
- Builds are reproducible and checksums are published. The TypeScript core's
  `.wasm` already is.
- The hosted package registry ships at 1.0, with its meta information API
  ([package-registry#1](https://github.com/ComlineProject/package-registry/issues/1)).

## Docs and project

- The docs describe 1.0 as it ships: guides, references, feature-support
  tables, and the tutorial and examples.
- The deprecation and changelog process from the
  [promises](phases.md#from-the-10-announcement) is written down.
- Each repository has a licence, a security policy saying how to report a
  vulnerability, and contributing notes.
