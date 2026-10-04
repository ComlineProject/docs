# Getting started

## Install

At the moment the is no proper `comline` releases in crates.io, so install **From source** below.

After installing from any of the two options, you should now have access to the `comline` binary (which should be at `~/.cargo/bin`). You can check by doing:

```bash
comline --help
```


### From Source (Github)
```bash
git clone https://github.com/ComlineProject/cli
cd cli
cargo install --path .
```

### From Cargo (crates.io)

`comline` is on crates.io but there is no proper releases being done yet, so build from source by doing the following:


A `cargo install comline` from crates.io, and OS packages (Fedora, Arch,
Windows, macOS), are planned — packaging is tracked in
[`ComlineProject/distributions`](https://github.com/ComlineProject/distributions).



## Create a project

```bash
comline new my-api
cd my-api
```

You get:

```
my-api/
├── config.idp        # package manifest
├── comline.toml       # where generated code goes (all-commented by default)
├── src/
│   └── main.ids      # a sample schema
└── .gitignore        # ignores .comline/
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
    message: string
    language: Language
}
```

## Build

```bash
comline build
```

This compiles and validates the schemas, then freezes the result as version
`0.0.1` in a content-addressable store under `.comline/`. Later builds
[bump the version automatically](reference/versioning.md) by the largest change
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
declares `rust#1.70.0`); output lands under `generated/` by default. Change where
and how in [`comline.toml`](reference/comline-toml.md):

```toml
[generate]
out    = "src/generated"
layout = "{{language}}/{{namespace}}.{{ext}}"
```

Today `rust` and `typescript` are the generators.

## Next

- [Overview](guide/overview.md) — the whole pipeline
- [IDL guide](guide/idl/index.md) — the schema language
- [Generating code](guide/codegen/generating-code.md) — the full `generate` surface
- [CLI reference](reference/cli.md) — every command and flag
