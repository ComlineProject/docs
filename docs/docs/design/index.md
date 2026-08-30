# Design

Design records for Comline — the *why* behind a decision and the state of its
rollout, not a usage guide. For how to *use* a feature, see the
[Guide](../guide/idl/index.md).

Each page carries a status and links the issues / PRs that carry it out.

## Decisions

- [Consumer generation configuration](consumer-generation-config.md) — where
  generated code goes and who owns that choice (`config.idp` vs `comline.toml`).
- [Multi-version generation](multi-version-generation.md) — emitting bindings for
  several historical package versions at once. *Implemented.*
- [IR freezing & the version state](ir-generation.md) — freezing into `.comline/`,
  automatic versioning, and the `comline clean` redesign. *Partly implemented.*
- [Codegen by language](codegen-by-language.md) — worked examples of one schema
  across Rust, Python, TypeScript, Luau. *Sketch.*
