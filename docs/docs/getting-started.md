# Getting started

## Install

`comline` isn't released on crates.io or as an OS package yet, so build it
from source. You need a Rust toolchain ([rustup](https://rustup.rs/)) and
`git`:

```bash
git clone https://github.com/ComlineProject/cli
cd cli
cargo install --path .
```

This puts the `comline` binary in `~/.cargo/bin`. Check it's on your `PATH`:

```bash
comline --help
```

`cargo install comline` and OS packages (Fedora, Arch, Windows, macOS) are
planned; packaging is tracked in
[`ComlineProject/distributions`](https://github.com/ComlineProject/distributions).

## Create a project

```bash
comline new my-api
cd my-api
```

You get:

```text
my-api/
├── config.idp        # package manifest
├── comline.toml       # where generated code goes (all-commented by default)
├── src/
│   └── main.ids      # a sample schema
└── .gitignore        # ignores .comline/deps-cache/
```

`src/main.ids`:

```ids
/// The language a greeting is written in.
enum Language {
    English
    Spanish
    Japanese
}

struct Greeting {
    message: char[max 256]
    language: Language
}
```

Every string and list needs a maximum, so a decoder can refuse an oversized
value before allocating it. `char[max 256]` is a string of at most 256
characters. To set one for the whole package instead, see
[default maximums](guides/idl/settings.md#default-maximums); the rules are in
[Types](guides/idl/types.md#bounds).

## Build

```bash
comline build
```

This compiles and validates the schemas, then freezes the result as a build,
`0.1.0-dev.1`, in a content-addressable store under `.comline/`. Builds lead up
to a release; when you want a version consumers see, run `comline release`
(the first is `0.1.0`), and later releases
[take the bump automatically](reference/versioning.md) from the largest change
since the last one.

Validate without freezing — safe for editors and pre-commit hooks:

```bash
comline check
```

## Generate code

```bash
comline generate
```

Targets come from `code_generation.languages` in `config.idp` (the scaffold
declares `rust#1.85.0`, the Rust generator's floor); output lands under `generated/` by default. Change where
and how in [`comline.toml`](reference/congregation/comline-toml.md):

```toml
[generate]
out    = "src/generated"
layout = "{{language}}/{{namespace}}.{{ext}}"
```

Today `rust` and `typescript` are the generators.

## Next

- [Overview](guides/index.md) — the whole pipeline
- [IDL guide](guides/idl/index.md) — the schema language
- [Generating code](guides/codegen/generating-code.md) — the full `generate` surface
- [CLI reference](reference/tools/cli.md) — every command and flag
