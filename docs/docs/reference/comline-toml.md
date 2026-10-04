# `comline.toml`

Consumer-owned configuration for `comline generate`: where generated code goes,
in what layout, in what form, and for which package versions. It is committed,
never frozen, and never part of a published package. With no `comline.toml` (or
an all-commented one) the defaults below apply and targets come from
`config.idp`'s `code_generation.languages`.

For the task-oriented walkthrough see [Generating code](../guide/codegen/generating-code.md).

## `[generate]`

Defaults for every target.

| Key | Type | Default | Meaning |
|---|---|---|---|
| `out` | string (path) | `"generated"` | Output root, relative to `comline.toml`. |
| `layout` | string (template) | `"{{language}}/{{namespace}}.{{ext}}"` | Path of each generated file under `out`. Handlebars, strict. |
| `mode` | `"code"` \| `"lib"` \| `"dylib"` | `"code"` | Emit form. `code` is implemented for every generator; `lib` for `rust`; `dylib` is planned — see [Library generation](../guide/codegen/library-generation.md). |
| `package_versions` | `"latest"` \| `"all"` \| list | `"latest"` | Which package versions to emit — see [below](#package_versions). |
| `default_framing` | string | — | Wire framing for protocols that don't pick one with [`@framing`](../guide/idl/protocol.md#protocol-annotations) — see [below](#default_framing). |

## `[[generate.target]]`

One block per target you want to pin or override. Any key from `[generate]` may
be repeated here to override it for this target only.

| Key | Type | Meaning |
|---|---|---|
| `language` | string | **Required.** Must be one the manifest declares under `code_generation.languages`. |
| `lang_version` | string | Optional; selects a version-specific generator. Defaults to what `config.idp` declared. |
| `out`, `layout`, `mode`, `package_versions`, `default_framing` | — | Per-target override of the `[generate]` value. |
| `flatten` | bool | `lib`/`dylib` only, target-only (no `[generate]` default): write the crate straight into `out` instead of `out/<language>/`. See [below](#flatten). |

```toml
[generate]
out    = "generated"
layout = "{{language}}/{{namespace}}.{{ext}}"

[[generate.target]]
language     = "rust"
lang_version = "1.70.0"
out          = "src/generated"
```

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
| `"all"` | Every committed version in the project's history. |
| `["0.3.0", "0.4.0"]` | Exactly those versions (version strings or commit hashes). |

Anything but `"latest"` reads the content-addressable store, so the project must
have been built at least once. Selecting more than one version **requires**
`{{package_version}}` in `layout` — otherwise every version writes to the same
paths. Old schemas are emitted with the *current* generator.

```toml
[generate]
package_versions = "all"
layout           = "{{language}}/{{package_version}}/{{namespace}}.{{ext}}"
```

## `default_framing`

The wire framing the generated `connect` / `serve` helpers use for any
`protocol` that does not set its own [`@framing`](../guide/idl/protocol.md#protocol-annotations).
Unset ⇒ the generator's built-in default (a compact datagram framing for Rust).

| Value | Effect |
|---|---|
| `"jsonrpc"` (`"json-rpc"`, `"jsonrpc-2.0"`) | JSON-RPC 2.0 framing. |
| `"datagram"` (`"comline.datagram"`) | The datagram default, stated explicitly. |

A value the target generator doesn't recognise leaves its built-in default in
place. A single protocol overrides the package setting either way with
`@framing` — including `@framing = "datagram"` to opt back out of a `jsonrpc`
default.

```toml
[generate]
default_framing = "jsonrpc"

[[generate.target]]
language        = "rust"
default_framing = "datagram"   # this target only
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

## Forward-looking

```toml
# Generate bindings for a registry dependency rather than the local schemas.
# Parsed but not yet operational — needs dependency resolution (core#6).
[generate.dependencies.stdlib]
out     = "src/gen/stdlib"
targets = ["rust"]
```
