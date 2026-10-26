# Branch rules

How changes reach a repository's default branch. Applied to
[`runtime`](https://github.com/ComlineProject/runtime) so far; other
repositories follow as they gain gates.

## Every change

- Goes through a pull request. Nobody pushes to the default branch directly.
- The default branch can't be deleted or force-pushed.
- Merges only when every required check passes. Nobody can skip them,
  admins included.
- Is up to date with the default branch before it merges, so the checks ran
  against what it merges into.

## Required checks: `runtime`

- `Rust project - stable`, `- beta`, `- nightly`: build and test.
- `wasm32 core`: the core builds for `wasm32` without `std`.
- `ffi`: the C ABI.
  - `comline.h` matches its source.
  - The conformance vectors pass through it from Rust, from C (static,
    dynamic, sanitized) and from Node (`wasm32`).
- `ffi miri`: the C ABI's tests under Miri.
- `fuzz (decode_no_panic)`, `fuzz (framing_decode)`,
  `fuzz (packed_canonical)`, `fuzz (seed_vs_derive)`, `fuzz (stream_split)`,
  `fuzz (ffi_feed)`, `fuzz (ffi_vs_core)`: 60 seconds per target.
- `instruction counts`: no benchmark, the core's or the C ABI's, grows more
  than 1% unless the pull request accepts it.

## The `reports` branch: `runtime`

- Holds the latest `rust.bench.json` and `rust.fuzz.json`. The docs fetch
  them each time the site builds.
- Not the default branch, so no ruleset covers it.
- Written only by CI: the bench workflow on every push to the default branch,
  the fuzz workflow nightly. Never by a pull request's run.
- One commit per report, never force-pushed, so its history is the series.

## Review

- A pull request needs one approval, from the code owner where it touches an
  owned file.
- A push after approval dismisses the approval.
- The admin may merge without review, through a pull request only.

## Owned files: `runtime`

Listed in [`.github/CODEOWNERS`](https://github.com/ComlineProject/runtime/blob/main/.github/CODEOWNERS):

- `.github/`, all of it: the workflows, their scripts, and `CODEOWNERS`.
- `runtime/core/benches/accepted-regressions.toml`: the ledger of accepted
  regressions.

## Accepting a regression

- Append an entry to `runtime/core/benches/accepted-regressions.toml`: the
  pull request's number, the benchmark, the maximum growth, the reason.
- It counts only for that pull request, only for that benchmark, and only up
  to that growth.
- An entry that isn't needed fails the gate. Existing entries can't change.
- Renaming or removing a benchmark needs a `[[removed]]` entry; a renamed one
  is compared with its old count.
- The failing job's summary prints the entry to paste.
