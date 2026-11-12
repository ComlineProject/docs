# CLI

`comline` drives the workflow around schemas: scaffold, validate, freeze
versions, compare them, generate code. This page is the quick reference; the
canonical long-form guide — output format, watch mode, completions, editor
integration — lives with the CLI at
[`ComlineProject/cli` → `docs/cli.md`](https://github.com/ComlineProject/cli/blob/main/docs/cli.md).
`comline <cmd> --help` is always authoritative.

## Install

Since it is not published to crates.io yet, you can build from source:

```sh
git clone https://github.com/ComlineProject/cli
cd cli
cargo install --path .
```

## Pipeline

```text
parse → resolve imports → validate → (freeze into .comline/) → (generate code)
```

`check` stops after validate. `build` adds the freeze step and records a version.
`generation` also stops after validate — it does **not** freeze — then writes code.
`diff` reads two frozen versions and reports what changed.

## Commands

`deps` and `generation` are groups. `deps` has `add`, `accept`, `pin`, `remove` and `list`; `generation` is
itself the command that writes code, and has `clean` beneath it to remove it. Run
`comline deps --help` or `comline generation --help` for a group's own synopsis.

| Command | What it does |
| --- | --- |
| `comline new <name> [--git]` | Scaffold `<name>/` with `config.idp`, `comline.toml`, `src/main.ids`, `.gitignore`. `--git` also runs `git init`. |
| `comline deps add <name> <dir>` / `comline deps add <name> --git <uri> --commit <sha> --version <v>` | Add a dependency to `config.idp`, imported as `use <name>::…`: resolved first (a git pin is fetched into `.comline/deps-cache/`), then written with its `hash` pinned. `--no-hash` skips the pin. If it has [`@unverified`](../../../guides/idl/protocol.md#giving-up-a-guarantee) protocols, what each gives up is shown and, on a terminal, you're asked to accept it (default no); without a terminal it refuses (exit `2`) unless `--accept-unverified`. |
| `comline deps accept <name>[::<protocol>] [--yes]` | Accept what a dependency's [`@unverified`](../../../guides/idl/protocol.md#giving-up-a-guarantee) protocols give up: shows each one's given-up guarantees and reason, then writes `accept_unverified` into its `config.idp` entry, leaving the rest as written. Only protocols not already accepted for exactly their current set are asked about. On a terminal you're asked (default no); without one it refuses (exit `2`) unless `--yes` (`-y`). |
| `comline deps pin <name> [--commit <sha> --version <v>] [--accept-unverified]` | Re-resolve a dependency whose content changed and rewrite its `hash` to what was just compiled, so the build stops failing on the old pin; an entry without a hash gains one. Nothing is written for a dependency that doesn't resolve, and it says so when the pin is already current. `--commit` with `--version` moves a git dependency to another commit as well. If the new content gives up more through `@unverified` than the entry accepts, it asks as `deps add` does; without a terminal it refuses (exit `2`) unless `--accept-unverified`. |
| `comline deps remove <name> [--dry-run]` | Remove a dependency's entry from `config.idp`, leaving the rest as written. Refused while a schema still imports it (each `use` is listed with its file and line), or when a schema doesn't parse, since then it can't tell. `--dry-run` shows the entry it would remove. A git dependency's checkout stays in `.comline/deps-cache/`. |
| `comline deps list [--json]` | List the declared dependencies by name: the source (path, or git URI at its commit and version), the pin (or `unpinned`) and what's accepted of its `@unverified` protocols. Read-only, and nothing is fetched. `--json` prints the same as JSON. |
| `comline check` | Parse, resolve and validate. No `.comline/` write (beyond fetching git dependencies), no version bump — safe for editors, hooks, CI. |
| `comline fix [--edition <n>] [--dry-run]` | Apply the fixes Comline attaches to what it reports about the language: add a missing `specification_version` to `config.idp`, and replace each use of a keyword or type the package's [edition](../../versioning.md#editions) deprecates or removes, when it has a replacement; uses without one are listed to change by hand. `--edition <n>` checks and fixes the schemas under edition `n` and moves `config.idp` to it, unless a removed word without a replacement is left (exit `1`). Moving back is refused. `--dry-run` lists the fixes and writes nothing. |
| `comline inspect [--json]` | Show each protocol's format, framing and handshake, with their parameters and where each came from (`@framing`/`@handshake`, `config.idp`, or core's default), then every guarantee, held or given up, with the cause, the `@unverified` reason and whether it's accepted. No `.comline/` write. `--json` prints the same as JSON. See [comline inspect](inspect.md). |
| `comline build [--watch] [--reconcile <hash>]` | Compile, validate, and freeze a build into `.comline/` under a pre-release version (`0.3.0-dev.2`); print the changelog, the bump, and the next release. `--reconcile <hash>` puts a head dropped in a Git merge back beside the current one, so the build [reconciles the two](../../../guides/ir/cas.md); the output says when a build reconciled. A project with [unbounded strings or lists](../../../guides/idl/types.md#every-string-and-list-has-a-maximum) fails with each position listed and the `settings` block to add; on a terminal, the build offers to write it with maxima you type in. Before freezing, proves every declared `code_generation.languages` target against this binary's generators ([Language versions](../../../guides/codegen/generating-code.md#language-versions)). Releasing is `comline release`. |
| `comline generation` (short: `gen`) `[--target <lang>] [--out <dir>] [--layout <tpl>] [--mode <m>] [--external-std] [--no-external-std] [--validate-on-decode <when>] [--dry-run] [--list] [--watch]` | Validate (no freeze), then write generated code. Wire numbers and the rest of the [facts](../../versioning.md#number) come from the last build when nothing changed since, else are worked out as the next build would assign them, provisional until a release; no build is needed. Location/layout from [`comline.toml`](../../package/congregation/comline-toml.md); targets from there or `config.idp`. A target can use an [external generator](../../../developer/extending/generators.md) (`generator = "<path>"`) and map [encodings](../../../developer/extending/encodings.md#5-map-it-to-a-type). |
| `comline release [1.0] [--raise <level> --reason <text>] [--yes]` | Build, then release: create the version from the highest bump since the last release ([builds and releases](../../versioning.md#builds-and-releases)). `--raise patch\|minor\|major` goes higher, with a `--reason` recorded with the release; it never lowers. `1.0` makes a `0.x` package stable after showing what that commits to (its protocols, and what's worth settling first). Raising to major and `1.0` ask on a terminal; without one they refuse (exit `2`) unless `--yes` (`-y`). |
| `comline diff <old> [<new>]` | Show schema changes between two built versions. Each argument is a version (`0.2.0`), a commit hash (4+ chars), or `HEAD` (`<new>` default). |
| `comline doc [--out <dir>] [--version <v>] [--changelog-from <v>] [--format <f>] [--open]` | Write the package's documentation for every version (each release, dev build and the unreleased working state), each into `<out>/<format>/<version>/` with the changelog from the version before it: Markdown pages (an index, one page per module with its `//!` header, every declaration's `///` docs and each protocol's wire summary, a changelog, an mkdocs/zensical `nav.yml`), `--format html` for a self-contained static site with the same content, a search box, a version picker and a page comparing versions, or `--format json` for the documentation model. Built versions are cached, so a run re-renders only the unreleased state and new versions; `--version` documents one built version. Defaults from [`comline.toml`](../../package/congregation/comline-toml.md#doc)'s `[doc]`. `comline doc open [<format>]` (or `--open` after a render) opens the result with the system's default handler, rendering first if it isn't there. No `.comline/` write. See [comline doc](doc.md). |
| `comline conformance --impl <command> [--encoding <name>]... [--corpus <dir>] [--timeout <secs>] [--json]` | Run an implementation of an encoding against its vectors. The package's declared [`encodings`](../../../developer/extending/encodings.md) ship vectors beside their profiles (`profiles/x.vectors.json`); `--impl` is a process speaking the [ops protocol](../../conformance/wire.md#the-ops-protocol), run once with a cleared environment, a time limit (`--timeout`, 60 s) and a capped stdout. `--encoding` limits the run to one encoding (repeatable); `--corpus` runs a corpus laid out like the runtime's `runtime/conformance` instead, which is how the official encodings are proven. A failed or unimplemented case, or an unproven profile fact, exits `1`. `--json` prints the report as JSON on stdout instead (nothing else on stdout; the exit code is the same): `format` (`1`), `implementation` (`command` and the `version` it reported, with its `protocol`), `encodings` (each with `name`, `kind`, `listed_by_implementation`, `passed`, `total`, `facts` as `{fact, value, proven, reason}` and `cases` as `{id, outcome, detail}` where `outcome` is `pass`, `fail` or `not_implemented`), `totals` (`encodings`, `cases`, `passed`, `problems`) and `verdict` (`conforms` or `fails`). See [Formats and framings](../../../developer/extending/encodings.md#3-write-vectors-and-prove-an-implementation). |
| `comline generation clean [--dry-run] [--target <lang>]` | Remove what `generation` wrote: the output root, or the individual generated files. `--target <lang>` (`-t`) removes only that language's output; a language no target matches is an error, as it is for `generation --target`. Never touches `.comline/`. |
| `comline reset [--force] [--dry-run]` | **Destructive.** Delete `.comline/` — the whole version history, no undo — *and* generated code. Next `build` starts over at `0.1.0-dev.1`. On a terminal it shows how many versions will be lost and makes you type `reset`; without a terminal it refuses (exit `2`) unless `--force`. |
| `comline completions <shell>` | Print a completion script to stdout. `bash` `zsh` `fish` `powershell` `elvish`. |
| `comline targets [--features [--json]]` | Print one `language#version` per line to stdout — the token syntax `config.idp`'s `code_generation.languages` expects, at the generator's floor — then the versions it handles and has verified, for every generator this binary was compiled with. Ignores `--path`: it reflects the build, not a project. `--features` also lists what each generator supports, feature by feature ([Languages](../../languages/index.md)); `--json` prints that as JSON. |

`--out` / `--layout` / `--mode` override one target and need `--target` when
several are configured. `COMLINE_GENERATE_OUT` / `_LAYOUT` / `_MODE` do the same
from the environment, for every target. `--external-std` makes generated code
reference std's own package — `comline_std` for rust, `@comline/std` for
typescript — instead of inlining it, and `--no-external-std` inlines it;
either overrides [`comline.toml`](../../package/congregation/comline-toml.md)'s
`[generate] external_std`, which itself defaults to on in `lib` mode and off
in `code` mode. `--validate-on-decode collect|first` overrides
[`[generate] validate_on_decode`](../../package/congregation/comline-toml.md#validate_on_decode),
whether decoding runs the schema's `@validators` (also
`COMLINE_GENERATE_VALIDATE_ON_DECODE`). The default is `collect`; turning it
off is a give-up written in `comline.toml` with its reason
(`{ off = "why" }`), and `generation` notes it per target.
Each target's files are drawn as a tree. `--list` prints them one per line
instead, with the schema each came from — and, when several package versions
are generated at once, the version each line belongs to. `--dry-run` writes
nothing and reports either way. Today `rust` and `typescript` are the generators, and both do `code`
and `lib` mode.

## Global flags

| Flag | Effect |
| --- | --- |
| `-p`, `--path <DIR>` | Run against `<DIR>` instead of the current directory. |
| `-v`, `--verbose` (repeatable: `-vv`, `-vvv`) | Raise log verbosity (info / debug / trace) for `comline-core` diagnostics. |
| `-q`, `--quiet` | Only errors. Conflicts with `-v`. |
| `--plain` | No color, symbols, emoji or spinner — for logs and CI. |

`RUST_LOG` overrides the verbosity flags. `NO_COLOR` strips color. stdout is
reserved for machine output (`completions` and `targets` write there);
everything else goes to stderr.

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | success |
| `1` | ran but failed — invalid schema, unresolved `diff` argument, generator or filesystem error |
| `2` | precondition not met — not a Comline project, nothing built yet, `reset` / a release not confirmed, or unverified protocols not accepted (also `clap` usage errors) |

## Versioning

`build` bumps the package version automatically by the largest schema change
since the last build. See [Versioning rules](../../versioning.md).
