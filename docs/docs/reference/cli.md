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
| `comline check` | Parse, resolve and validate. No `.comline/` write, no version bump — safe for editors, hooks, CI. |
| `comline build [--release] [--watch]` | Compile, validate, freeze a new immutable version into `.comline/`; print the changelog and the bump. `--release` is currently a no-op. |
| `comline generate [--target <lang>] [--out <dir>] [--layout <tpl>] [--mode <m>] [--watch]` | Validate (no freeze), then write generated code. Location/layout from [`comline.toml`](comline-toml.md); targets from there or `config.idp`. |
| `comline diff <old> [<new>]` | Show schema changes between two built versions. Each argument is a version (`0.2.0`), a commit hash (4+ chars), or `HEAD` (`<new>` default). |
| `comline clean [--dry-run]` | Remove `.comline/` and `generate` output. Next `build` restarts history at `0.0.1`. |
| `comline completions <shell>` | Print a completion script to stdout. `bash` `zsh` `fish` `powershell` `elvish`. |

`--out` / `--layout` / `--mode` override one target and need `--target` when
several are configured. `COMLINE_GENERATE_OUT` / `_LAYOUT` / `_MODE` do the same
from the environment, for every target. Today `rust` is the only generator and
`code` the only mode.

## Global flags

| Flag | Effect |
|---|---|
| `-p`, `--path <DIR>` | Run against `<DIR>` instead of the current directory. |
| `-v` / `-vv` / `-vvv` | Raise log verbosity (info / debug / trace) for `comline-core` diagnostics. |
| `-q`, `--quiet` | Only errors. Conflicts with `-v`. |
| `--plain` | No color, symbols, emoji or spinner — for logs and CI. |

`RUST_LOG` overrides the verbosity flags. `NO_COLOR` strips color. stdout is
reserved for machine output (only `completions` writes there); everything else
goes to stderr.

## Exit codes

| Code | Meaning |
|---|---|
| `0` | success |
| `1` | ran but failed — invalid schema, unresolved `diff` argument, generator or filesystem error |
| `2` | precondition not met — not a Comline project, or nothing built yet (also `clap` usage errors) |

## Versioning

`build` bumps the package version automatically by the largest schema change
since the last build. See [Versioning rules](versioning.md).
