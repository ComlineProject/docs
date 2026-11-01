# Generator protocol

How the CLI talks to a code generator, and to a documentation renderer. For a
walkthrough, see
[Generators](../guide/extending/generators.md); to point a target at one, see
the [CLI reference](cli.md#commands) and
[`comline.toml`](congregation/comline-toml.md#generator).

The Rust definitions are in `codegen/src/protocol.rs` of the
[generation](https://github.com/ComlineProject/generation) repository.

## Version

**Protocol version: `0`** (`PROTOCOL_VERSION`). While Comline is in its early
days, the protocol may change incompatibly, and the number moves when it does.
An additive change keeps the number: a new field with a default, or a new
request that only goes to a program whose `Description` says it handles it
(`Render` was added this way).

The protocol is also pinned to an **IR format** (`IR_FORMAT`), the stamp on
`.comline/` that `comline-core` owns. A generator accepts the IR formats it
lists and refuses others.

## Transport

- One request is written to the generator's **stdin**, then stdin closes.
- One response is read from its **stdout**.
- Each is a single **CBOR** document, in the encoding `comline-core` stores
  its IR with (name-tagged fields).
- A generator process serves one request per run. The CLI starts it once for
  `Describe` and once for each `Generate` or `Render`.
- Exit successfully whenever a response was written, an error response
  included. A nonzero exit or a response that isn't a protocol response is a
  failure.

## Request

| Field | Type | Meaning |
|---|---|---|
| `protocol` | integer | the protocol version the sender speaks |
| `ir_format` | integer | the IR format of every frozen unit in the body |
| `body` | `Describe`, `Generate(GenerateRequest)` or `Render(RenderRequest)` | what is asked |

`protocol` and `ir_format` come first, and a generator reads them before the
body. A mismatch is reported even when the body has a shape the generator
doesn't know.

### `Describe`

No fields. Asks which languages, versions, protocol versions and IR formats the
generator handles.

### `Generate`

Generate one target. A `GenerateRequest` holds:

| Field | Type | Meaning |
|---|---|---|
| `mode` | `Code` or `Lib` | emit sources only, or a whole package with its manifest |
| `schemas` | list of (namespace, frozen units) | every schema in the package, as compiled IR |
| `package` | `{ name, version }` | package identity, for the manifest a `Lib` build emits; unused by `Code` |
| `target` | `{ language, version }` | the language and version the target declared; also what selected this generator |
| `wire_format` | string | the package's wire format, canonical: `packed@1` (the default), `json@1` or `msgpack@1` |
| `external_std` | bool | reference `std` as its own crate instead of inlining it; only a generator that knows how acts on it |
| `validate_on_decode` | `Off`, `Collect` or `First` | whether decoding runs `@validators` checks |
| `async_api` | bool | async handlers and senders for protocols on a connection |
| `encodings` | map name to mapping | the implementation of each encoding, in this target's language |

- The framing isn't a field. Core writes the package's framing into each
  protocol's IR as its `framing` property.
- A mapping is `{ type_path, package?, version? }`: the type implementing the
  encoding, and optionally the package it comes from and the version
  requirement. The keys are canonical names (`jsonrpc`, `datagram`,
  `datagram@2` for the official ones, the declared name for others). The CLI
  fills the map from the package's declarations and the consumer's overrides
  ([Map it to a type](../guide/extending/encodings.md#5-map-it-to-a-type)).
- `mode` is `Code` or `Lib`. `dylib` isn't part of the protocol today.

### `Render`

Render a package's documentation, for [`comline doc`](tools/doc.md). Only sent
to a program whose `Description` lists the renderer at the model version. A
`RenderRequest` holds:

| Field | Type | Meaning |
|---|---|---|
| `renderer` | string | the renderer's id, from `Description.renderers`: `markdown` |
| `model_version` | integer | the documentation model's version (`DOC_MODEL_VERSION`, `1`), readable without parsing `model` |
| `model` | string | the documentation model as JSON text, in the shape of [`doc-model/1.json`](../schemas/doc-model/1.json) |
| `options` | `{ links, version, versions, notes }` | see below |

| Option | Meaning |
|---|---|
| `links` | a dependency's name (or `std`) to the base URL of its docs |
| `version` | set when this render is one version of a multi-version site: the version's folder (`0.2.0`, `0.3.0-dev.2`, `unreleased`). The files land in `<site>/<version>/`, so the site's shared files are at `../`. Absent for a site of its own. |
| `versions` | set for a site's index render: every version, oldest first, each `{ id, release, kind, model }`. `release` is the release a dev build leads to (`0.3.0` for `0.3.0-dev.2`), itself for a release, `unreleased` for the working tree; `kind` is `release`, `dev` or `unreleased`; `model` is that version's model as JSON, with its `changelog` from the version before it in the list. The files land at the site's root, and the request's own `model` is the newest version's. |
| `notes` | plain-text notes for every page of this version: what an old version's documentation lacks |

A renderer accepts every option and ignores the ones it has no use for. The
answer is `Render(Generated)`: files, checked like a generator's.

**Several versions.** [`comline doc`](tools/doc.md) documents every version
with one `Render` per version (with `version` set), then one for the site's
index (with `versions` set). A per-version request carries one model, like a
single-version one, so a renderer that ignores `version` still works: it
renders each version on its own. The index request goes only to a renderer
whose `Description` entry sets `sites`. Both options are additive, so the
protocol version stays `0`.

**The model's version.** The documentation model follows the same rule as the
protocol: an additive change keeps `model_version` (a new unit, type or change
kind, or a new field that may be absent), so a renderer skips a `kind` it
doesn't know and ignores unknown fields. A consumer validating strictly against
`doc-model/1.json` should expect the schema to grow. Only an incompatible
change bumps the version.

## Response

| Variant | Carries |
|---|---|
| `Describe(Description)` | the answer to `Describe` |
| `Generate(Generated)` | the answer to `Generate` |
| `Render(Generated)` | the answer to `Render`: the rendered files |
| `Error { message }` | the request was refused or generation failed |

### `Description`

| Field | Meaning |
|---|---|
| `languages` | one entry per generator; a language with several floors has several |
| `protocols` | `(min, max)` protocol versions it accepts, inclusive |
| `ir_formats` | the IR formats it accepts |
| `renderers` | the documentation renderers it offers, each `{ id, model_versions, version, sites }`; empty, or absent from an older program, when it offers none. `version` is the renderer's own version, part of `comline doc`'s cache key (empty when absent); `sites` says it renders a multi-version site's index (`false` when absent) |

A language entry holds:

| Field | Meaning |
|---|---|
| `id` | the language name a package declares: `rust`, `typescript` |
| `ext` | the source file extension: `rs`, `ts` |
| `versions` | `floor`, `changes`, `verified_up_to` and `forward_compatible`: which versions of the language it handles |
| `support` | one entry per feature it states: `feature`, `state`, `note`, `tracking`, `since` |

The CLI picks the entry whose `floor` is the newest one at or below the
target's version.

### `Generated`

| Field | Meaning |
|---|---|
| `files` | each `{ path, contents }`: a path relative to the target's output root, and the file's bytes |
| `diagnostics` | strings worth telling the user that didn't stop generation; the CLI shows each as a warning |

## Checks the CLI makes

- **Describe:** the CLI's protocol version must be inside `protocols`, and its
  IR format must be in `ir_formats`. Otherwise it refuses the generator and names
  both sides.
- **Language:** the generator must offer the target's language at the target's
  version, or the CLI refuses it.
- **Renderer:** for `comline doc`, the program must list the format in
  `renderers`, with the CLI's model version in `model_versions`, or the CLI
  refuses it before sending `Render`.
- **Output:** every path, then the total size, is checked before anything is
  written.

### Path rules

A path in a response must:

- be non-empty and `/`-separated;
- be relative, with no leading `/`;
- have no `.` or `..` components and no empty components;
- contain no `\`, no `:` and no NUL.

A response with any bad path is refused whole, and nothing from it is written.

### Limits

| | Limit |
|---|---|
| time per call | `timeout` on the target, 60 seconds by default |
| stdout | 256 MiB |
| total generated file contents | 256 MiB |
| stderr shown | the first 64 KiB, prefixed with the generator's file name |
| `.wasm` memory | 1 GiB |

A `.wasm` generator also gets no preopened directories, no environment and no
network, and no arguments beyond `argv[0]`. A native generator gets an empty
environment and isn't otherwise sandboxed.

## Rust helpers

The `comline_codegen::protocol` module exports:

- `Request`, `RequestBody`, `GenerateRequest`, `RenderRequest`,
  `RenderOptions`, `Response`, `Description`, `RendererInfo`, `Generated` and
  the types in the tables above;
- `encode` and `decode`, to and from CBOR;
- `respond(registry, bytes)`, which answers one request without panicking, and
  `handle`, which does the same on bytes;
- `serve_stdio(registry)`: a generator process's whole `main`. A registry
  holds renderers too (`Registry::register_renderer`), so one binary can
  generate, render, or both. The official Markdown renderer is
  `comline-doc-markdown` in the generation repository.
