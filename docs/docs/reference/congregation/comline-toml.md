# `comline.toml`

Consumer-owned configuration for `comline generate`: where generated code goes,
in what layout, in what form, and for which package versions. Its `[doc]`
table configures `comline doc`. It is committed,
never frozen, and never part of a published package. With no `comline.toml` (or
an all-commented one) the defaults below apply and targets come from
`config.idp`'s `code_generation.languages`.

For the task-oriented walkthrough see [Generating code](../../guide/codegen/generating-code.md).

## `[generate]`

Defaults for every target.

| Key | Type | Default | Meaning |
|---|---|---|---|
| `out` | string (path) | `"generated"` | Output root, relative to `comline.toml`. |
| `layout` | string (template) | `"{{language}}/{{namespace}}.{{ext}}"` | Path of each generated file under `out`. Handlebars, strict. |
| `mode` | `"code"` \| `"lib"` \| `"dylib"` | `"code"` | Emit form. `code` and `lib` are implemented for `rust` and `typescript`; `dylib` is planned — see [Library generation](../../guide/codegen/library-generation.md). |
| `package_versions` | `"latest"` \| `"all"` \| list | `"latest"` | Which package versions to emit — see [below](#package_versions). |
| `external_std` | bool | on in `lib`, off in `code` | Reference `std` as its own package instead of inlining it — see [below](#external_std). |
| `validate_on_decode` | `"off"` \| `"collect"` \| `"first"` | `"off"` | Whether decoding a value runs its [`@validators`](../../guide/idl/validator.md) — see [below](#validate_on_decode). |
| `async` | bool | `false` | Generate protocols on a connection for an async driver — see [below](#async). |
| `encodings` | table | — | Which type implements each encoding (format, framing, handshake) in the generated code — see [below](#encodings). |
| `only` | list of strings | — | Generate just these languages, out of the ones `config.idp` declares — see [below](#only). |

## `[[generate.target]]`

One block per declared language you want to configure. Any key from
`[generate]` may be repeated here to override it for that language only.

A block **configures** a language; it does not choose which languages are
generated. That comes from `config.idp` alone — a declared language with no
block takes the `[generate]` defaults, several blocks for one language give
several outputs, and a block naming a language the congregation doesn't
declare is an error. To generate *fewer* than the package declares, use
[`only`](#only).

| Key | Type | Meaning |
|---|---|---|
| `language` | string | **Required.** Must be one the manifest declares under `code_generation.languages`. |
| `lang_version` | string | Optional; the toolchain version to generate for. Defaults to what `config.idp` declared, and may raise it but never lower it ([Language versions](../../guide/codegen/generating-code.md#language-versions)). |
| `out`, `layout`, `mode`, `package_versions`, `external_std`, `validate_on_decode`, `async` | — | Per-target override of the `[generate]` value. |
| `generator` | string (path) | A generator outside the CLI, a `.wasm` or a native executable, relative to `comline.toml`'s directory. Unset, the built-in generator for `language` is used. See [below](#generator). |
| `timeout` | integer (seconds) | With `generator` only: how long each call to it may take. At least 1; default 60. |
| `encodings` | table | Per-target mapping, over `[generate]`'s, name by name. |
| `flatten` | bool | `lib`/`dylib` only, target-only (no `[generate]` default): write the crate straight into `out` instead of `out/<language>/`. See [below](#flatten). |

```toml
[generate]
out    = "generated"
layout = "{{language}}/{{namespace}}.{{ext}}"

[[generate.target]]
language     = "rust"
lang_version = "1.88.0"
out          = "src/generated"
```

### `generator`

```toml
[[generate.target]]
generator = "tools/comline-gen-go.wasm"
language  = "go"
timeout   = 120
```

Runs a generator that is its own program, speaking the
[generator protocol](../generator-protocol.md). `language` picks among the
languages it offers, and may be left out if it offers one; it must still be one
`config.idp` declares. A `.wasm` runs sandboxed; anything else runs as a native
process, unsandboxed. The limits and path rules are in
[Generators](../../guide/extending/generators.md#limits).

### `encodings`

```toml
[generate]
encodings = { "com.acme.lines@1" = "acme_lines::LinesFraming" }

[[generate.target]]
language  = "rust"
encodings = { "com.acme.lines@1" = { type = "acme_lines::LinesFraming", package = "acme-lines", version = "0.1" } }
```

Maps an encoding's name to the type that implements it, in the target's
language. A value is the type alone, or a table with `type` and optionally
`package` and `version`. For each encoding the package uses, the first of these
that answers wins: this table (the target's over `[generate]`'s), then the
`map` the declaring package suggests in its `config.idp`. An encoding that is
used and has no mapping is a generation error. See
[Map it to a type](../../guide/extending/encodings.md#5-map-it-to-a-type).

### `flatten`

`layout` only governs `code` mode's one-file-per-schema paths — a `lib`-mode
target ignores it entirely (`comline generate` warns if one is set) and
always writes the crate's fixed internal shape (`Cargo.toml`, `src/lib.rs`, a
file per schema under `src/`) rooted at `out/<language>/`, so two `lib`
targets can safely share one `out` without their files colliding.

A target with its own dedicated `out` doesn't need that disambiguation —
`flatten = true` skips it, writing the crate straight into `out`:

```toml
[[generate.target]]
language = "rust"
mode     = "lib"
out      = "../my-rust-crate/"
flatten  = true   # crate lands at out/, not out/rust/
```

Only set this when the target's `out` is exclusively its own — flattening a
shared `out` across more than one `lib` target reintroduces the collision
the default layout avoids.

### `external_std`

Comline's standard library is implicitly available to every package, so
`std/http` and `std/validators` are part of every generation request. This
decides whether their code is **copied into** your generated output or
**referenced** from std's own pre-generated package:

| Language | Package |
|---|---|
| `rust` | `comline_std` (a crate, pinned by git rev) |
| `typescript` | `@comline/std` (an npm package, by semver range) |

It defaults to on in `lib` mode — a buildable package should depend on std
rather than vendor it — and off in `code` mode, which has no manifest to
declare a dependency in. In `code` mode with it on, the generated file names
what to install in a comment at the top.

`--external-std` and `--no-external-std` override it for one run.

Neither package is published yet, so a `lib` target that references one needs
it linked locally (`npm link`, a path override) until that changes — which is
already true of `@comline/runtime` for any package with a protocol.

### `validate_on_decode`

Generated code always carries a schema's [`@validators`](../../guide/idl/validator.md)
checks as `validate()` / `validate_first()`, for you to call. This decides
whether **decoding** calls them too:

| Value | Decoding a value that fails its checks |
|---|---|
| `"off"` | succeeds; nothing runs until you call `validate()` |
| `"collect"` | fails, with every failed check |
| `"first"` | fails, with the first failed check |

It's yours to choose rather than the schema's: it changes what decoding costs,
and a form that wants every problem at once and a hot path that wants to stop
early want different things from the same type. With it on, a provider also
refuses a call whose arguments fail their checks, the same way it refuses
arguments that don't decode.

Today only the `rust` generator runs validators; `typescript` ignores this.
`--validate-on-decode` and `COMLINE_GENERATE_VALIDATE_ON_DECODE` override it.

### `async`

A protocol on a [connection](../../guide/idl/protocol.md#calls-in-both-directions)
is generated for a blocking driver by default. `async = true` generates it for
an async one instead:

- **`rust`:** async handlers, `<Proto>AsyncDispatcher` and `<Proto>AsyncSender`,
  and an async package `serve` / `accept` / `connect`, for the runtime's
  `AsyncConnection` on any executor — see
  [Rust connections](../../languages/rust/connections.md#async). A `lib`
  package turns on the runtime's `async` feature.
- **`typescript`:** nothing changes; its handlers and senders return Promises
  either way.

Every protocol is on a connection unless it's lockstep (the `datagram`
framing, or JSON-RPC with no client-provided protocol); those are the same
either way, and `comline generate` warns when `async = true` changes nothing. Like
`external_std`, it's a consumer's choice: the same package can be generated
async for one application and blocking for another.

### `only`

Generate a subset of the languages `config.idp` declares, for a checkout that
doesn't need all of them:

```toml
[generate]
only = ["rust"]
```

A name the congregation doesn't declare is an error, so a typo fails loudly
instead of quietly generating nothing. `--target` narrows a single run the
same way.

This is also the escape hatch when a declared language has no generator in
your `comline` build: declaring a language means you mean it, so a missing
generator is an error rather than a silent skip, and `only` is how you say
you want fewer.

## `[doc]`

Settings for [`comline doc`](../tools/doc.md). Each key but `renderer`,
`timeout` and `links` has a flag that overrides it.

| Key | Type | Default | Meaning |
|---|---|---|---|
| `out` | string (path) | `"docs/api"` | Output directory, relative to `comline.toml`. `--out` overrides it. |
| `format` | string | `"markdown"` | `markdown` (pages), `html` (a static site), `json` (the documentation model, `model.json`), or another renderer id `renderer` offers. `--format` overrides it. |
| `renderer` | string (path) | — | A renderer outside `comline`: a `.wasm` (run sandboxed under wasmtime) or an executable, relative to `comline.toml`'s directory. Run exactly like an external [`generator`](#generator). Unset, the built-in renderer for `format` is used. |
| `timeout` | integer (seconds, ≥ 1) | `60` | The wall-time limit for each call to `renderer`. |
| `links` | table | — | Where each dependency's docs live, by the name the package gives it (or `std`): a base URL. A type from a dependency listed here links to `<base>/<module>/#<anchor>`; one that isn't is plain text. |
| `changelog_from` | string | — | Add a changelog from this built version (a version or commit hash) to the documented one. `--changelog-from` overrides it. |

```toml
[doc]
out = "site/docs/api"
links = { std = "https://example.com/std" }
changelog_from = "0.1.0"
```

## Layout variables

| Variable | Value |
|---|---|
| `{{language}}` | target language, e.g. `rust` |
| `{{namespace}}` | the schema's namespace, `/`-joined |
| `{{ext}}` | the generator's file extension, e.g. `rs` |
| `{{lang_version}}` | the declared language / toolchain version |
| `{{spec_version}}` | the manifest's `specification_version` |
| `{{package_version}}` | the package version being generated (see below) |

## `package_versions`

| Value | Effect |
|---|---|
| `"latest"` (default) | The working tree only. No `.comline/` read. `{{package_version}}` is the last committed version (empty if never built). |
| `"all"` | Every release in the project's history (not the builds between them). |
| `["0.3.0", "0.4.0"]` | Exactly those versions: releases, builds (`0.3.0-dev.2`) or commit hashes. |

Anything but `"latest"` reads the content-addressable store, so the project must
have been built at least once. Selecting more than one version **requires**
`{{package_version}}` in `layout` — otherwise every version writes to the same
paths. Old schemas are emitted with the *current* generator.

```toml
[generate]
package_versions = "all"
layout           = "{{language}}/{{package_version}}/{{namespace}}.{{ext}}"
```

## `default_framing` (moved)

The framing is part of the schema, since both ends have to agree on it, so it
moved to the package: `config.idp`'s `wire = { framing = "..." }`
([Wire defaults](../../guide/packages/index.md#wire-defaults)). A
`default_framing`, in `[generate]` or in a target, is an error that names the
line to write there instead:

```text
`default_framing` moved from comline.toml to config.idp
  help: drop it here, and declare the package's framing in config.idp:
      wire = { framing = "jsonrpc" }
```

## Precedence

Lowest to highest, applied field by field:

```
built-in defaults → [generate] → [[generate.target]] → COMLINE_GENERATE_* env → CLI flags
```

- `COMLINE_GENERATE_OUT` / `COMLINE_GENERATE_LAYOUT` / `COMLINE_GENERATE_MODE` —
  apply to **every** target (a CI global). Empty values are ignored.
- `--out` / `--layout` / `--mode` — apply to **one** target and need `--target`
  when more than one is configured.

## Editor support

`comline.toml` has a JSON Schema, served at
`https://comlineproject.github.io/docs/schemas/comline-toml/0.x.json`. With it an
editor completes keys, checks values, and shows each key's description on hover.
`comline new` writes the pointer as the first line of the file:

```toml
#:schema https://comlineproject.github.io/docs/schemas/comline-toml/0.x.json
```

In VS Code, the [Comline extension](https://github.com/ComlineProject/comline-vscode)
gives `comline.toml` its own language, and the Comline language server checks it
against the package next to it, with or without the line. On top of the schema's
checks it reports:

- a `language` that `config.idp` doesn't declare;
- a version no built-in generator handles;
- an `encodings` key that no package in view declares;
- an encoding the package uses but leaves unmapped;
- a `generator` path that isn't a file.

It completes `language` from `config.idp` and `encodings` keys from their
declarations, and its quick fixes correct a misspelt key or value, or declare a
missing language in `config.idp`. It never runs a generator.

In other editors, any TOML language server that reads the `#:schema` directive
picks the schema up, such as [Taplo](https://taplo.tamasfe.dev/).

## Forward-looking

```toml
# Generate bindings for a registry dependency rather than the local schemas.
# Parsed but not yet operational — needs dependency resolution (core#6).
[generate.dependencies.stdlib]
out     = "src/gen/stdlib"
targets = ["rust"]
```
