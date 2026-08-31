# Playground & tutorial

Status: **discussion** — a `web/` scaffold exists (SvelteKit `playground` and
`tutorial` apps, a `compilation-queue-server`, shared Svelte libs), last touched
early 2024 and not wired to the current `core` / `generation` / `runtime` ·
Affects `ComlineProject/web`, and how `core` / `generation` build to WASM

## Goal

A browser experience where you type a schema and, live:

- see the IR and the validation diagnostics (inline, LSP-style);
- pick a target language + mode and see the generated code;
- run a **runtime demo** — send a message through the call system to a handler
  and watch it serialise, route, dispatch, and come back.

Two properties are non-negotiable:

- **Correctness** — the playground runs *the same code* as the CLI, not a
  re-implementation. Diagnostics and generated output are byte-identical.
- **Responsiveness** — the edit → IR → diagnostics → code loop keeps up with
  typing (target < ~1 frame of jank on the editor thread).

## The core decision: WASM vs a compile server

| | client-side WASM | compile-queue server |
|---|---|---|
| latency | instant (local) | network round-trip + queue |
| offline | yes | no |
| hosting | static, free | a service to run and scale |
| can run `cargo build` (real `lib` / `dylib`, native runtime) | **no** | yes |
| one source of truth with the CLI | yes (same crates) | yes (same binary) |

`core` (parse → IR → validate) and `comline-codelib-gen` (codegen) are the
real-time loop, and both are WASM-friendly: pure Rust, `once_cell` / `eyre`, and
a pure-Rust tree-sitter runtime (`rust-sitter` → `tree-sitter-c2rust`). No
`std::fs`, threads, or `libloading` on that path.

**Recommendation: hybrid.**

- **WASM for the hot loop** — `core` + `comline-codelib-gen` compiled to
  `wasm32-unknown-unknown` via `wasm-bindgen`, run in a **Web Worker** so the
  editor thread never blocks. This covers `code` mode for every language and
  emitting the `lib`-mode file tree.
- **The `compilation-queue-server`, later and optional** — only for what WASM
  genuinely can't do: `cargo build` of a generated crate, a real multi-process
  runtime demo. v1 can ship without it.

## The runtime demo

The full runtime is transport + call framing + routing + dispatch. In a browser:

- **serialisation** (`rmp-serde` / `serde_json`), **call framing** (JSON-RPC),
  **in-process routing** — all WASM-able.
- **real sockets** — no. Use an **in-memory loopback**: client → a fake "wire" →
  runtime → handler, all in one context, where the wire is an inspectable queue
  you can pause and delay to visualise latency, ordering, and back-pressure
  (this is what the `tutorial` README's "ping, requests/responses counts,
  graphs, simulate machines" asks for).
- **the handler's language** — generated code is Rust or TS. A Rust handler
  means another compile; **a TS handler runs natively in the browser**. So the
  runtime demo generates TS types + a thin TS runtime shim, the user writes the
  handler in a JS/TS editor, and the playground wires the loopback. Rust
  handlers would need the compile server.

## The "same as the CLI" contract

- One `comline-playground` crate (in `web/` or `generation`) depends on
  `comline-core` + `comline-codelib-gen` and exposes a small `wasm-bindgen`
  surface: `parse`, `validate`, `generate(target, mode)`.
- Reuse `render_validation_error` and the diagnostics module so errors render
  exactly as the CLI prints them.
- Pin the crate revisions and show them in the UI — a playground bug report is
  then reproducible against a known `core` / `generation`.

## Performance notes

- **Web Worker** for the WASM; `postMessage` the source in, structured
  diagnostics + files out.
- **Debounce** recompiles ~150–250 ms; cancel the in-flight worker call on a new
  keystroke.
- Exploit `core`'s `IncrementalInterpreter` for cheap reparse.
- **WASM size** — the tree-sitter grammar tables dominate. Measure; lazy-load
  the module on first edit; cache it under a version-stamped URL (Cache API) so
  a revisit is warm.
- `wasm-opt`, `opt-level = "z"` vs `"s"`, and SIMD are worth trying once there
  is a size number to move.

## Playground vs tutorial

- **Playground** — a free-form scratchpad. Shareable: encode the editor state in
  the URL (with a size ceiling), or a tiny gist-like store if that ceiling
  bites.
- **Tutorial** — guided, step-gated lessons, each a pre-filled editor + an
  expected-output panel, building up structs → enums → protocols → errors →
  validators → imports → generate → runtime. The `tutorial` README wants each
  step to *simulate* running machines with distinct local/remote panels and live
  stats — the loopback runtime above is the engine for that.
- Both consume the same WASM module and the same component library.

## Where it lives / embedding

- The `web/` repo holds the `playground` and `tutorial` apps and shared libs.
- The docs site (Zensical, static) can embed a `<comline-playground>` **web
  component** into guide / tutorial pages, so "edit this schema and watch it
  compile" is inline with the prose — the strongest form of the docs being the
  home.
- To decide: one deploy or three (docs / playground / tutorial); one domain or
  subdomains; and whether the existing SvelteKit apps are carried forward or the
  playground is rebuilt as a framework-neutral web component the docs can host
  directly.

## Open questions

- **v1 scope** — compile + diagnostics + codegen only, or include the runtime
  loopback from the start?
- **Runtime-demo language** — TS-only (browser-native), or also Rust (needs the
  compile server)?
- **The `compilation-queue-server`** — revive it for real `cargo build` /
  multi-process demos, or drop it and commit to WASM-only for v1?
- **Framework** — reuse the SvelteKit scaffold, or rebuild as a web component so
  the Zensical docs can embed it without a Svelte runtime?
- **Tutorial content** — authored inside the `tutorial` app, or as Markdown in
  `docs/` and rendered by both?
- **Version sync** — the playground pins `core` / `generation` revs; it inherits
  the same [git-rev treadmill](generation.md#open-questions) until those crates
  cut releases.
