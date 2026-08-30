# Packages & dependencies

A Comline **package** (historically *congregation*) is a directory with a
manifest and one or more schema files:

```
my-api/
├── config.idp        # the manifest — package identity + declarations
├── comline.toml       # consumer-side: where generated code goes (see below)
├── src/
│   └── *.ids          # the schemas
└── .comline/          # content-addressable store (appears after the first build)
```

## The manifest — `config.idp`

```
congregation my_api
specification_version = 1

code_generation = {
    languages = {
        rust#1.70.0 = {}
        python#3.11.0 = {}
    }
}
```

| Field | Meaning |
|---|---|
| `congregation` | the package name — a Comline identifier (letters, digits, `_`) |
| `specification_version` | which version of the schema language these files are written against |
| `code_generation.languages` | the **capability list**: `language#lang_version` targets this package *can* be generated as. Bare entries — `= {}` is required and takes no options. |
| `dependencies` | other packages this one imports (identity + integrity hash) |
| `publish_registries` | named registries this package publishes to (planned — [see below](#publishing-planned)) |

The manifest is **frozen**: it lowers to IR units and is content-addressed into
every built version, so a published version carries its own declarations. It
never contains an output path — that is a consumer choice and lives in
`comline.toml`.

## `.comline/` — the store

After the first `comline build`, a `.comline/` directory holds the
[content-addressable store](../ir/cas.md) (`objects/`) and the version ref
(`refs/heads/main`). It is the authoritative, append-only history of the
package's versions, and the only copy of it — nothing pushes it anywhere yet.

The `comline new` scaffold git-ignores it, which suits tests and examples. A
package with a version history worth keeping should either commit `.comline/` or,
once [publishing](#publishing-planned) exists, publish it.

!!! warning
    `comline clean` deletes `.comline/` — see
    [Versioning rules](../../reference/versioning.md#history-model).

## Consumer side — `comline.toml`

Where generated code lands, in what layout, for which versions — none of which
belongs to the package author — is set by whoever runs `comline generate`, in a
separate, non-frozen `comline.toml`. See
[Generating code](../codegen/generating-code.md) and the
[`comline.toml` reference](../../reference/comline-toml.md).

## Publishing (planned)

Publishing is not part of the `comline` CLI. It is being built in a companion
tool, `comlinepm` (`ComlineProject` package-management repos), and is only
partly wired up.

A package declares where it can publish in `config.idp`:

```
publish_registries = {
    mainstream = std::publish::MAINSTREAM_REGISTRY
    my_registry  = { uri = "https://example.test/index/" }
    dev_registry = { uri = "local://{{package_path}}/.registry/" }
}
```

Then:

```
comlinepm registry login <name>
comlinepm registry publish --registries "mainstream my_registry"
```

`publish` builds the package, then pushes the frozen store to each named
registry. **Status:** a `local://` (directory) registry works — it copies the
frozen project in. A hosted `https://` registry server exists as a stub only;
`logout` and the official `MAINSTREAM_REGISTRY` URL are `todo!()`.

## Dependencies (not implemented)

A `dependencies` block is parsed, but the referenced packages are not fetched,
pinned or stored, and their schema shapes do not yet feed this package's version
or code generation. Tracking: `ComlineProject/core` #6. The reasoning and the
intended version-bump behaviour are in
[Consumer generation configuration](../../design/consumer-generation-config.md).
