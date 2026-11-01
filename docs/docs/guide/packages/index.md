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
id = "3f2a9c41d07e4b1c8a65f2e0d91b7c34"
specification_version = 1

code_generation = {
    languages = {
        rust#1.85.0 = {}
        typescript#5.0 = {}
    }
}
```

| Field | Meaning |
|---|---|
| `congregation` | the package name — a Comline identifier (letters, digits, `_`) |
| `id` | the package's identity: 32 lowercase hex digits, random. `comline new` writes it, and `comline build` adds one to a package without it, as one line after `congregation`, with a note. A rename keeps it; a copy of the package must change it. Changing it is a major change. See [Compatibility facts](../../reference/versioning.md#compatibility-facts) |
| `specification_version` | which version of the schema language these files are written against |
| `code_generation.languages` | the **capability list**: `language#lang_version` targets this package *can* be generated as, each version the oldest toolchain the output must build on, which `comline build` proves ([Language versions](../codegen/generating-code.md#language-versions)). Bare entries — `= {}` is required and takes no options. |
| `dependencies` | other packages this one imports — see [Dependencies](#dependencies) |
| `settings` | package-wide authoring policy, enforced at build time — see [Settings](../idl/settings.md) |
| `wire` | the package's wire format and framing — see [Wire defaults](#wire-defaults) |
| `handshake` | what a protocol with no `@handshake` runs before its first call: `"comline@1"` (the default) or `"none"` — see [Giving up a guarantee](../idl/protocol.md#giving-up-a-guarantee) |
| `encodings` | the formats, framings and handshakes this package defines, each with a profile — see [Extending Comline](../extending/encodings.md) |
| `publish_registries` | named registries this package publishes to (planned — [see below](#publishing-planned)) |

The manifest is **frozen**: it lowers to IR units and is content-addressed into
every built version, so a published version carries its own declarations. It
never contains an output path — that is a consumer choice and lives in
`comline.toml`.

## Wire defaults

Both ends of a connection have to frame and encode calls alike, so the
package says how, once:

```idp
wire = { format = "packed@1" framing = "datagram@2" }
```

| Key | Values | Default |
|---|---|---|
| `format` | `"packed@1"`, `"json@1"`, `"msgpack@1"` | `"packed@1"`: fixed-width fields with no tags or names — see [`packed@1`](../../reference/wire/packed.md) |
| `framing` | `"datagram@2"`, `"datagram"` (`"datagram@1"`), `"jsonrpc"` | `"datagram@2"`: every protocol on a [connection](../idl/protocol.md#calls-in-both-directions) |

Either key can be left out, and so can `wire`: the defaults are what a package
that says nothing gets. The values are strings, quoted.

- **`framing`** applies to every protocol with no `@framing` of its own. The
  build writes it into each one, so it's part of the schema, and changing it
  is a major change.
- **`format`** is what the generated code encodes with: Rust's and
  TypeScript's `Format`. Changing it is a major change too.
- **JSON-RPC carries JSON.** A package with a JSON-RPC protocol (through its
  own `@framing` or through `wire.framing`) can't declare another `format`;
  that's a build error naming the protocol. Leaving `format` out is fine:
  the default then applies to the other protocols only.
- **A target has to support the format.** TypeScript has no MessagePack codec
  yet, so `comline build` refuses `msgpack@1` in a package that declares
  TypeScript.

These used to be the consumer's choice, in `comline.toml`'s `default_framing`.
That key is now an error that hands back the `wire` line to write instead.

## `.comline/` — the store

After the first `comline build`, a `.comline/` directory holds the
[content-addressable store](../ir/cas.md) (`objects/`) and the version ref
(`refs/heads/main`). It is the authoritative, append-only history of the
package's versions, and the only copy of it — nothing pushes it anywhere yet.

Commit it. Nothing publishes it yet, so a clone without it starts over with no
recorded versions. The `comline new` scaffold's `.gitignore` ignores only
`.comline/deps-cache/`, where [git dependencies](#dependencies) are fetched.

!!! warning
    `comline reset` deletes `.comline/` (behind a confirmation). `comline clean`
    does not — see [Versioning rules](../../reference/versioning.md#history-model).

## Consumer side — `comline.toml`

Where generated code lands, in what layout, for which versions — none of which
belongs to the package author — is set by whoever runs `comline generate`, in a
separate, non-frozen `comline.toml`. See
[Generating code](../codegen/generating-code.md) and the
[`comline.toml` reference](../../reference/congregation/comline-toml.md).

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
like any other package. Your package uses that compile as it is: a
dependency's schemas aren't compiled again under your settings, its own
package defaults (such as its `handshake`) stay with them, and its warnings
are its authors' and aren't repeated in your build. A git fetch that fails (no network, a commit that
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
