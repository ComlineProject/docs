# CLI

`comline` drives the workflow around schemas: scaffold, validate, freeze
versions, compare them, generate code. This page is the quick reference; the
canonical long-form guide — output format, watch mode, completions, editor
integration — lives with the CLI at
[`ComlineProject/cli` → `docs/cli.md`](https://github.com/ComlineProject/cli/blob/main/docs/cli.md).
`comline <cmd> --help` is always authoritative.

## Install

Not published to crates.io yet — build from source:

```bash
git clone https://github.com/ComlineProject/cli
cd cli
cargo install --path .
```

## Pipeline

```
parse → resolve imports → validate → (freeze into .comline/) → (generate code)
```

`check` stops after validate. `build` adds the freeze step and records a version.
`generate` also stops after validate — it does **not** freeze — then writes code.
`diff` reads two frozen versions and reports what changed.

## Commands

| Command | What it does |
|---|---|
| `comline new <name> [--git]` | Scaffold `<name>/` with `config.idp`, `comline.toml`, `src/main.ids`, `.gitignore`. `--git` also runs `git init`. |
| `comline add <name> <dir>` / `comline add <name> --git <uri> --commit <sha> --version <v>` | Add a dependency to `config.idp`, imported as `use <name>::…`: resolved first (a git pin is fetched into `.comline/deps-cache/`), then written with its `hash` pinned. `--no-hash` skips the pin. If it has [`@unverified`](../guide/idl/protocol.md#giving-up-a-guarantee) protocols, what each gives up is shown and, on a terminal, you're asked to accept it (default no); without a terminal it refuses (exit `2`) unless `--accept-unverified`. |
| `comline accept <name>[::<protocol>] [--yes]` | Accept what a dependency's [`@unverified`](../guide/idl/protocol.md#giving-up-a-guarantee) protocols give up: shows each one's given-up guarantees and reason, then writes `accept_unverified` into its `config.idp` entry, leaving the rest as written. Only protocols not already accepted for exactly their current set are asked about. On a terminal you're asked (default no); without one it refuses (exit `2`) unless `--yes` (`-y`). |
| `comline check` | Parse, resolve and validate. No `.comline/` write (beyond fetching git dependencies), no version bump — safe for editors, hooks, CI. |
| `comline build [--watch]` | Compile, validate, and freeze a build into `.comline/` under a pre-release version (`0.3.0-dev.2`); print the changelog, the bump, and the next release. Before freezing, proves every declared `code_generation.languages` target against this binary's generators ([Language versions](../guide/codegen/generating-code.md#language-versions)). Releasing is `comline release`. |
| `comline generate [--target <lang>] [--out <dir>] [--layout <tpl>] [--mode <m>] [--external-std] [--no-external-std] [--validate-on-decode <when>] [--dry-run] [--list] [--watch]` | Validate (no freeze), then write generated code. Location/layout from [`comline.toml`](congregation/comline-toml.md); targets from there or `config.idp`. |
| `comline release [1.0] [--raise <level> --reason <text>] [--yes]` | Build, then release: create the version from the highest bump since the last release ([builds and releases](versioning.md#builds-and-releases)). `--raise patch\|minor\|major` goes higher, with a `--reason` recorded with the release; it never lowers. `1.0` makes a `0.x` package stable after showing what that commits to (its protocols, and what's worth settling first). Raising to major and `1.0` ask on a terminal; without one they refuse (exit `2`) unless `--yes` (`-y`). |
| `comline diff <old> [<new>]` | Show schema changes between two built versions. Each argument is a version (`0.2.0`), a commit hash (4+ chars), or `HEAD` (`<new>` default). |
| `comline clean [--dry-run]` | Remove generated code (the `generate` output root or files). Never touches `.comline/`. |
| `comline reset [--force] [--dry-run]` | **Destructive.** Delete `.comline/` — the whole version history, no undo — *and* generated code. Next `build` starts over at `0.0.1`. On a terminal it shows how many versions will be lost and makes you type `reset`; without a terminal it refuses (exit `2`) unless `--force`. |
| `comline completions <shell>` | Print a completion script to stdout. `bash` `zsh` `fish` `powershell` `elvish`. |
| `comline targets [--features [--json]]` | Print one `language#version` per line to stdout — the token syntax `config.idp`'s `code_generation.languages` expects, at the generator's floor — then the versions it handles and has verified, for every generator this binary was compiled with. Ignores `--path`: it reflects the build, not a project. `--features` also lists what each generator supports, feature by feature ([Languages](languages/index.md)); `--json` prints that as JSON. |

`--out` / `--layout` / `--mode` override one target and need `--target` when
several are configured. `COMLINE_GENERATE_OUT` / `_LAYOUT` / `_MODE` do the same
from the environment, for every target. `--external-std` makes generated code
reference std's own package — `comline_std` for rust, `@comline/std` for
typescript — instead of inlining it, and `--no-external-std` inlines it;
either overrides [`comline.toml`](congregation/comline-toml.md)'s
`[generate] external_std`, which itself defaults to on in `lib` mode and off
in `code` mode. `--validate-on-decode off|collect|first` overrides
[`[generate] validate_on_decode`](congregation/comline-toml.md#validate_on_decode),
whether decoding runs the schema's `@validators` (also
`COMLINE_GENERATE_VALIDATE_ON_DECODE`).
Each target's files are drawn as a tree. `--list` prints them one per line
instead, with the schema each came from — and, when several package versions
are generated at once, the version each line belongs to. `--dry-run` writes
nothing and reports either way. Today `rust` and `typescript` are the generators, and both do `code`
and `lib` mode.

## Global flags

| Flag | Effect |
|---|---|
{% for row in global_flags %}| {{ row.flag }} | {{ row.effect }} |
{% endfor %}

`RUST_LOG` overrides the verbosity flags. `NO_COLOR` strips color. stdout is
reserved for machine output (`completions` and `targets` write there);
everything else goes to stderr.

## Exit codes

| Code | Meaning |
|---|---|
| `0` | success |
| `1` | ran but failed — invalid schema, unresolved `diff` argument, generator or filesystem error |
| `2` | precondition not met — not a Comline project, nothing built yet, `reset` / a release not confirmed, or unverified protocols not accepted (also `clap` usage errors) |

## Versioning

`build` bumps the package version automatically by the largest schema change
since the last build. See [Versioning rules](versioning.md).
