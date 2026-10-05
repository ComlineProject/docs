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

```idp
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
| `dependencies` | other packages this one imports — see [Dependencies](#dependencies) |
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
    `comline reset` deletes `.comline/` (behind a confirmation). `comline clean`
    does not — see [Versioning rules](../../reference/versioning.md#history-model).

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

## Dependencies

A package can import schemas from other packages it declares in `config.idp`:

```idp
dependencies = {
    shared_types = {
        path = "../shared-types"
    }

    net = {
        version = "1.2.0"
        uri = "https://github.com/acme/net"
        commit = "4f2c9e1"
        hash = "blake3:…"
    }
}
```

The key (`shared_types`, `net`) is a name you choose. What the entry contains
decides where the package comes from:

| Source | Written as | Resolved |
|---|---|---|
| Path | `path` (optional `hash`) | relative to this package's directory |
| Git | `version`, `uri`, `commit` (optional `hash`) | cloned once per pin into `.comline/deps-cache/`, using the `git` binary |
| Registry | `version`, `uri` (optional `hash`, `signature`) | **not supported yet** — there's no registry server, so `comline check` / `build` reject it |

`comline check` and `comline build` resolve every dependency, then compile it
like any other package. A git fetch that fails (no network, a commit that
doesn't exist) leaves nothing in the cache, so the next run fetches again and
reports git's own error.

- **Importing.** A dependency's schemas live under the name you gave it:
  `shared_types`'s `src/foo.ids` is imported as `use shared_types::foo::X`. An
  import that matches nothing fails the build
  ([Imports](../idl/use.md#when-nothing-matches)).
- **Direct dependencies only.** A dependency's own dependencies aren't
  importable from your package.
- **Pinning.** `hash` is a blake3 hash over the dependency's compiled schemas.
  If it doesn't match, the build fails. Without one, the build warns and prints
  the hash to pin.
- **Reproducible versions.** Each build vendors the resolved dependencies into
  the version it commits (a `dep_<name>` subtree in `.comline/`), so a version
  can be rebuilt from the store alone.
- **Versioning.** Adding a dependency is a minor bump and removing one is major.
  A dependency present in both versions is diffed like your own schemas, so a
  breaking change in it is a major bump for you and an additive one a minor
  bump.
- **In the editor.** The language server reads the same `dependencies` block,
  but never fetches anything. A path dependency, or a git pin `comline check`
  has already fetched, is indexed under its name: hover, go-to-definition and
  completion reach into it, and an import that matches nothing gets the build's
  error. A pin that isn't fetched yet gets a warning on its entry in
  `config.idp`, and imports from it aren't checked until it is. More in
  [Dependency packages in the editor](../../design/editor-dependency-packages.md).

`comline add` writes an entry for you, after resolving the dependency (a git pin
is fetched), with its `hash` pinned to what it just compiled:

```bash
comline add shared_types ../shared-types
comline add net --git https://github.com/acme/net --commit 4f2c9e1 --version 1.2.0
```

The rest of `config.idp` is left as written. `--no-hash` skips the pin, say for
a path dependency you're still working on.
