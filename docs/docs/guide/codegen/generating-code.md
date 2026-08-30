# Generating code

`comline generate` turns your compiled schemas into source code for a target
language. This page is the practical guide: what it produces, how to say where it
goes, and how to generate more than one version at once.

Status: this reflects the current CLI. `rust` is the only generator and `code`
the only mode so far; the configuration surface below is stable.

## The two files

Code generation is configured across two files with two different owners:

| File | Owner | In version control | Purpose |
|---|---|---|---|
| `config.idp` | the **package author** | committed, frozen into every published version | declares *what languages* the package can be generated as |
| `comline.toml` | the **consumer** (whoever runs `generate`) | committed, never frozen | says *where* generated code goes, in what layout, for which versions |

`config.idp` never contains an output path — where your bindings land is your
call, not the package author's, so it lives in `comline.toml`.

## Declaring targets — `config.idp`

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

Each entry is a bare `language#lang_version`. `lang_version` selects a
version-specific generator (e.g. Rust 1.70's output vs a later edition's). The
`= {}` is required and takes no options.

A declared language is a *capability*: "bindings for this language make sense for
this package." It does not force anyone to generate it, and it carries no output
path.

## Configuring output — `comline.toml`

```toml
[generate]
out              = "generated"                              # output root, relative to comline.toml
layout           = "{{language}}/{{namespace}}.{{ext}}"     # path of each file under the root
mode             = "code"                                   # code | lib | dylib   (only `code` today)
package_versions = "latest"                                 # latest | all | ["0.3.0", "0.4.0"]

# Optional: one block per target you want to pin or override.
[[generate.target]]
language     = "rust"
lang_version = "1.70.0"        # defaults to what config.idp declared
out          = "src/generated" # this target only
```

With no `comline.toml` (or an all-commented one) the defaults above apply and the
targets come from `config.idp`'s `code_generation.languages`.

**Precedence**, lowest to highest:

```
built-in defaults → [generate] → [[generate.target]] → COMLINE_GENERATE_* env → CLI flags
```

`COMLINE_GENERATE_OUT` / `_LAYOUT` / `_MODE` apply to every target (handy in CI);
`--out` / `--layout` / `--mode` apply to one target and need `--target` when
several are configured.

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
comline generate [--target <lang>] [--out <dir>] [--layout <tpl>] [--mode <m>] [--watch]
```

`generate` validates the project and writes the code. Unlike `comline build` it
does **not** freeze a version or write to `.comline/` — it is safe to run
repeatedly and from CI.

```bash
comline generate                              # every configured target, per comline.toml
comline generate --target rust                # just rust
comline generate --target rust --out ./bind   # override this target's output root
comline generate --watch                      # regenerate on schema / config change
```

`comline clean` removes the generated output (the whole `out` directory when it
is a dedicated one, e.g. `generated/`). It leaves `.comline/` alone —
`comline reset` is the command that discards the version history.

## What Rust output looks like

| Schema | Rust |
|---|---|
| `struct` | `#[derive(…)] pub struct` with `serde` derives |
| `enum` | `pub enum` |
| `protocol` | `pub trait` with a method per function |

Current limitation: cross-schema `import`s are not yet emitted as `use`
statements, so multi-file output can reference types it does not bring into
scope.

## Modes (planned)

`mode` selects the emit form. Only `code` — plain source text you drop into your
project — exists today. `lib` (a buildable crate skeleton) and `dylib` (that,
compiled, for a language runtime to load) are planned.

## Gotchas

- `generate` never changes the package version. Only `build` does.
- The default layout writes under `generated/`. Older CLI versions wrote flat
  into the project root; set `out = "."` and `layout = "{{namespace}}.{{ext}}"`
  for that.
- `comline.toml` is meant to be committed — the team and CI should agree on the
  layout. It is never part of a published package.
