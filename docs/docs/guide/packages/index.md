# Packages & dependencies

!!! note "Stub"
    This page will cover the package manifest, dependency resolution, and
    registries. The underlying design is in
    [Consumer generation configuration](../../design/consumer-generation-config.md).

A Comline **package** (historically *congregation*) is a set of schemas plus a
manifest, `config.idp`, that declares:

- the package **name** and `specification_version`
- **dependencies** on other packages (identity + integrity hash)
- **publish registries**
- the code-generation **capability list** — which `language#version` targets the
  package can be generated as

The manifest is frozen and content-addressed, so it travels with every published
version. Consumer-side choices — where generated code lands, which versions to
emit — live in a separate, non-frozen `comline.toml`; see
[Generating code](../codegen/generating-code.md).

## Status

Dependency *resolution* is not implemented yet: `dependencies` blocks are parsed
but not fetched, pinned, or stored. Tracking: `ComlineProject/core` #6.
