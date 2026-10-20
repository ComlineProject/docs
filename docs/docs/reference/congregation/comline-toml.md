# `comline.toml`

Consumer-owned configuration for `comline generate`: where generated code goes,
in what layout, in what form, and for which package versions. It is committed,
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
| `default_framing` | string | — | Wire framing for protocols that don't pick one with [`@framing`](../../guide/idl/protocol.md#annotations) — see [below](#default_framing). |
| `external_std` | bool | on in `lib`, off in `code` | Reference `std` as its own package instead of inlining it — see [below](#external_std). |
| `validate_on_decode` | `"off"` \| `"collect"` \| `"first"` | `"off"` | Whether decoding a value runs its [`@validators`](../../guide/idl/validator.md) — see [below](#validate_on_decode). |
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
| `lang_version` | string | Optional; selects a version-specific generator. Defaults to what `config.idp` declared. |
| `out`, `layout`, `mode`, `package_versions`, `default_framing`, `external_std`, `validate_on_decode` | — | Per-target override of the `[generate]` value. |
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

## `default_framing`

The wire framing the generated `connect` / `serve` helpers use for any
`protocol` that does not set its own [`@framing`](../../guide/idl/protocol.md#annotations).
Unset ⇒ the generator's built-in default (a compact datagram framing for Rust).

| Value | Effect |
|  ---  |  ---   |
| `"datagram"` (`"comline.datagram"`) | The datagram default, stated explicitly. |
| `"jsonrpc"` (`"json-rpc"`, `"jsonrpc-2.0"`) | JSON-RPC 2.0 framing. |
| `"datagram@2"` | The datagram framing with a request/reply marker and a protocol number: every protocol runs on a [connection](../../guide/idl/protocol.md#calls-in-both-directions). |

Any other value is an error naming the accepted ones, with a "did you mean"
for a near miss. (It used to fall back silently to datagram, so a typo only
showed up as a refused handshake.) A single protocol overrides the package setting either way with
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
