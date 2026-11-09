# Timings, size and coverage

How compile time and CI time are measured, along with the two other
measurements that flow the same way: artifact size and test coverage. None of
these are gated. They're published so a trend is visible on the
[Observatory](reports.md). The formats are in the Observatory's
[`DATA.md`](https://github.com/ComlineProject/observatory/blob/main/DATA.md#kinds).

## Flow

1. On every push to the default branch, a repository's `reports.yml` runs one
   job per measurement. Each job uses a shared action from
   `ComlineProject/observatory/.github/actions/` that writes one JSON report.
2. A `publish` job commits all of the reports to the repository's `reports`
   branch. It never runs on a pull request.
3. On a pull request, `reports.yml` runs only when the workflow itself
   changes. Everything but the publish runs then, so the change is proven
   before it merges.

## Compile time

`report-rust-compile` runs `cargo clean`, then `cargo build --timings` with
the workflow's arguments (`--workspace --release`). Cargo has no JSON output
for timings, so the action reads the unit data embedded in the HTML report.

```json
{ "format": 1, "commit": "…", "toolchain": "…", "run": "…",
  "runner": "github-hosted", "profile": "release",
  "total_seconds": 84.2, "units": { "comline-runtime": { "seconds": 12.7 } } }
```

- `total_seconds` is when the last unit ended. A crate's `seconds` sums its
  units, including the build script.
- Wall time depends on the machine, so the Observatory names the metric
  `seconds@<runner>` and only compares a runner with itself.

| Source | Report |
| --- | --- |
| runtime | `rust.compile.json` |
| core | `core.compile.json` |
| cli | `cli.compile.json` |

## CI time

CI time has no producer and no report file. The Observatory's collector reads
workflow runs from the GitHub API for every repository:

- Only completed runs on the default branch count, with the event `push`,
  `schedule` or `workflow_dispatch`. It reads the newest 1000 at most.
- Per workflow it records `duration_s`, `attempts` (above 1 means a rerun)
  and `conclusion` (pass or fail).

Pull request runs aren't counted, so a slow branch doesn't skew the series.

## Size

`report-size` records the bytes and gzip bytes of the listed artifacts.
Each artifact id names how it was built, for example
`ffi/cdylib/x86_64-linux-release` or `ffi/wasm32-release`.

| Source | What's measured |
| --- | --- |
| runtime | the C ABI crate: cdylib, staticlib, wasm32 |
| cli | the release binary |
| simulator | the wasm build, before and after `wasm-opt`, in both flavours |
| comline-typescript | the `npm pack` tarball and the built entry file |

## Coverage

Line and function coverage, plus branch coverage where the tool reports it,
in total and per unit. A unit is a crate in Rust and a top-level directory of
`runtime/src/` in TypeScript.

| Source | Tool |
| --- | --- |
| runtime, core, cli, generation | `report-rust-coverage` (cargo-llvm-cov) |
| comline-typescript | Node's built-in coverage, converted by `runtime/scripts/lcov-to-observatory.py` |

Higher coverage is better. For every number on this page except coverage,
lower is better.
