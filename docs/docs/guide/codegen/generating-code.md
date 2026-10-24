# Generating code

`comline generate` turns your compiled schemas into source code for a target
language. This page is the practical guide: what it produces, how to say where it
goes, and how to generate more than one version at once.

Status: this reflects the current CLI. `rust` and `typescript` are the
generators, and both do `code` and `lib`; the configuration surface below is
stable.

## The two files

Code generation is configured across two files with two different owners:

| File | Owner | In version control | Purpose |
|---|---|---|---|
| `config.idp` | the **package author** | committed, frozen into every published version | declares *what languages* the package can be generated as |
| `comline.toml` | the **consumer** (whoever runs `generate`) | committed, never frozen | says *where* generated code goes, in what layout, for which versions |

`config.idp` never contains an output path — where your bindings land is your
call, not the package author's, so it lives in `comline.toml`.

## Declaring targets — `config.idp`

```idp
congregation my_api
specification_version = 1

code_generation = {
    languages = {
        rust#1.85.0 = {}
        typescript#5.0 = {}
    }
}
```

Each entry is a bare `language#lang_version`: the language, and the **oldest
toolchain** its generated code must build on. The `= {}` is required and takes
no options. See [Language versions](#language-versions) for what the version
promises and how it's checked.

Declaring a language is what makes it generated: `comline generate` emits every
language listed here. The entry carries no output path — where the code lands is
the consumer's business, below — and a consumer who wants fewer says so with
`only`.

## Configuring output — `comline.toml`

```toml
[generate]
out              = "generated"                              # output root, relative to comline.toml
layout           = "{{language}}/{{namespace}}.{{ext}}"     # path of each file under the root
mode             = "code"                                   # code | lib   (dylib is not built yet)
package_versions = "latest"                                 # latest | all | ["0.3.0", "0.4.0"]
only             = ["rust"]                                 # generate just these, out of the declared languages

# Optional: one block per declared language you want to configure.
[[generate.target]]
language     = "rust"
lang_version = "1.88.0"        # defaults to what config.idp declared; may only raise it
out          = "src/generated" # this language only
```

With no `comline.toml` (or an all-commented one) the defaults above apply to
every language `config.idp` declares.

**A block configures a language; it doesn't choose which languages are
generated.** That comes from `config.idp` alone. A declared language with no
block takes the `[generate]` defaults, several blocks for one language give
several outputs, and a block naming a language the congregation doesn't declare
is an error rather than a silent no-op.

To generate fewer languages than the package declares — because this checkout
only needs some of them — list the ones you want in `[generate] only`, or pass
`--target` for a single run. A name `config.idp` doesn't declare is an error
there too, so a typo can't quietly stop generating something.

**Precedence**, lowest to highest:

```
built-in defaults → [generate] → [[generate.target]] → COMLINE_GENERATE_* env → CLI flags
```

`COMLINE_GENERATE_OUT` / `_LAYOUT` / `_MODE` apply to every target (handy in CI);
`--out` / `--layout` / `--mode` apply to one target and need `--target` when
several are configured.

## Language versions

The version in `rust#1.85.0` is a **minimum**: generated code builds on that
toolchain and every newer one, like Cargo's `rust-version`. Raising it can
unlock newer constructs, and lowering it gives them up.

**Each generator has a floor**, the oldest version it generates for, and
handles every version from there up. `comline targets` lists them:

```console
$ comline targets
rust#1.85.0  (1.85.0 or later; verified up to 1.99, and newer toolchains build its output)
typescript#5.0  (5.0 or later; verified up to 5.9)
```

`comline new` scaffolds the floor, which is the widest promise a package can
make.

### `comline build` proves every declaration

A declared version is a promise consumers rely on, so `comline build` checks
each `code_generation.languages` entry before it freezes a version. Any of
these fails the build, and nothing is frozen:

- **No generator handles it:** the version is below the generator's floor
  ("`rust#1.70.0` is older than the rust generator handles: it needs
  `rust#1.85.0` or later"), it isn't dotted numbers, or this `comline` was
  built without that language.
- **A dependency declares more:** if a dependency declares `rust#1.90.0`, its
  generated code needs Rust 1.90, so this package must declare at least that.
- **A feature isn't supported at that version:** the schemas use something
  the generator doesn't support there. The message names every use and, for
  a feature that's only supported from a later version, the version to
  declare.

The editor reports the same problems on the entry in `config.idp` as you
type.

### Raising the version in `comline.toml`

A consumer can set `lang_version` on a `[[generate.target]]` **higher** than
`config.idp` declares, for example to unlock an option that needs a newer
toolchain. Lower is an error: the package was only proven from its declared
version on.

A version never changes the wire, only the generated code. Peers whose code
was generated for different versions still talk to each other.

### Past what a generator has verified

Each generator states the newest toolchain its output has been verified
against. Declaring or raising a version past it still generates, with a
warning under `generation::unverified-version`. For a language whose newer
compilers promise to build older code, as Rust's do, there's no such limit.

To insist on verified targets, raise it to an error in the package's
[settings](../idl/settings.md):

```idp
settings = {
    diagnostics = {
        generation::unverified-version = {
            level = "error"
        }
    }
}
```

Every generated file's header also names the range it was generated for
(`// For Rust 1.85.0 or later; verified up to 1.99.`). A TypeScript `lib`
package lists `typescript` as an optional peer dependency at the declared
version and up.

## Layout templates

`layout` is a [Handlebars](https://handlebarsjs.com/) path rendered once per
schema. Variables:

| Variable | Value |
|---|---|
| `{{language}}` | the target language, e.g. `rust` |
| `{{namespace}}` | the schema's namespace, `/`-joined |
| `{{ext}}` | the generator's file extension, e.g. `rs` |
| `{{lang_version}}` | the declared language/toolchain version |
| `{{spec_version}}` | the IDL `specification_version` |
| `{{package_version}}` | the package version being generated (see below) |

```toml
layout = "{{namespace}}.{{ext}}"                              # flat: foo/bar.rs
layout = "{{language}}/{{namespace}}.{{ext}}"                  # default: rust/foo/bar.rs
layout = "{{language}}/{{package_version}}/{{namespace}}.{{ext}}"  # versioned
```

## Generating multiple versions

`package_versions` decides which package versions to emit bindings for:

- **`"latest"`** (default) — the working tree. No `.comline/` read. Here
  `{{package_version}}` is the last committed version (empty if you've never run
  `comline build`).
- **`"all"`** — every committed version in the project's history.
- **`["0.3.0", "0.4.0"]`** — specific versions (or commit hashes).

Anything but `"latest"` reads the content-addressable store, so the project must
have been built at least once. Because every version would otherwise write to the
same paths, selecting more than one version requires `{{package_version}}` in
`layout`:

```toml
[generate]
package_versions = "all"
layout           = "{{language}}/{{package_version}}/{{namespace}}.{{ext}}"
```

```
generated/rust/0.3.0/…
generated/rust/0.4.0/…
generated/rust/0.5.0/…
```

Old schemas are generated with the *current* generator — you get today's
idiomatic output for a past schema shape.

## Running it

```
comline generate [--target <lang>] [--out <dir>] [--layout <tpl>] [--mode <m>] [--dry-run] [--list] [--watch]
```

`generate` validates the project and writes the code. Unlike `comline build` it
does **not** freeze a version or write to `.comline/` — it is safe to run
repeatedly and from CI.

```bash
comline generate                              # every configured target, per comline.toml
comline generate --target rust                # just rust
comline generate --target rust --out ./bind   # override this target's output root
comline generate --dry-run                    # report without writing anything
comline generate --watch                      # regenerate on schema / config change
```

Each target's files are reported as a tree:

```
  ⚙️  language: typescript, version: 5.0, mode: lib
       generated/typescript/
       ├─ package.json
       ├─ src/
       │  ├─ index.ts
       │  ├─ std/
       │  │  └─ http.ts
       │  └─ types.ts
       └─ tsconfig.json
```

`--list` prints one line per file instead, naming the schema each came from
(`api.ids → generated/rust/api.rs`) — and the package version, when several are
generated at once. `--dry-run` and `--list` are independent: the first decides
whether anything is written, the second how it is reported.

`comline clean` removes the generated output (the whole `out` directory when it
is a dedicated one, e.g. `generated/`). It leaves `.comline/` alone —
`comline reset` is the command that discards the version history.

## What Rust output looks like

| Schema | Rust |
|---|---|
| `struct` | `#[derive(…)] pub struct` with `serde` derives |
| `enum` | `pub enum` |
| `protocol` | `pub trait` with a method per function |

A cross-schema reference (a type pulled in via `use`) is emitted as a
`crate`-qualified path (`crate::shared::Shared`), not a bare name — a
non-local schema (a declared dependency, or `std` when it is inlined) is
copied into the same generated output, under a module tree that mirrors its
namespace. `lib` mode wires that module tree up itself (`pub mod shared;` in
`src/lib.rs`); `code` mode does not write module declarations, so a project
using cross-schema references in `code` mode needs to declare matching `mod`
statements itself.

`std` is the exception, because
[`external_std`](../../reference/congregation/comline-toml.md#external_std)
is on by default in `lib` mode: a std type then resolves to
`comline_std::http::Request` and the crate depends on `comline_std` rather
than carrying a copy of it.

## What TypeScript output looks like

| Schema | TypeScript |
|---|---|
| `struct` | `export interface` |
| `error` | `export interface` (the payload) + `export class <Name>Error` |
| `enum` | `export enum` with string values |
| `protocol` | a client, a dispatcher, and a `serve<Proto>` helper against `@comline/runtime` |

A cross-schema reference is emitted as an `import type` from the schema that
declares it, by relative specifier:

```ts
import type { Greeting } from "./types.js";
```

An alias imports the name the other module actually exports
(`use types::Greeting as G` → `import type { Greeting as G }`), and a `use`
nothing refers to produces no import at all.

`std` again resolves to its own package when
[`external_std`](../../reference/congregation/comline-toml.md#external_std)
is on, by subpath import — the leading `std` segment drops, since
`@comline/std` is its own package root:

```ts
import type { Request } from "@comline/std/http";
```

The specifier is relative, so `code` mode assumes your `layout` keeps each
schema's namespace in the **file-name** position — every layout above does,
including the default. A layout that puts the namespace in a directory
position instead (`"{{namespace}}/index.{{ext}}"`) moves the files relative to
each other and the imports won't resolve.

In `lib` mode the namespace tree becomes the package's shape, so both of these
work:

```ts
import { types } from "my-api";        // types.Greeting
import { Greeting } from "my-api/types";
```

## Modes

`mode` selects the emit form. `code` (plain source text you drop into your
project) and `lib` (a buildable package) both work, for both generators;
`dylib` — that, compiled, for a language runtime to load — is planned.
[Library generation](library-generation.md) explains each mode and when to reach
for it.

## Gotchas

- `generate` never changes the package version. Only `build` does.
- The default layout writes under `generated/`. Older CLI versions wrote flat
  into the project root; set `out = "."` and `layout = "{{namespace}}.{{ext}}"`
  for that.
- `comline.toml` is meant to be committed — the team and CI should agree on the
  layout. It is never part of a published package.
