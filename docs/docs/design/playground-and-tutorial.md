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

**Scope for v1: everything** — compile + diagnostics + codegen + a working
runtime demo. The compile/codegen loop is language-agnostic from day one (it is
`core` + `comline-codelib-gen` in WASM); the *runtime demo* rolls out per
language by how runnable that language is in a browser (see
[Running handlers per language](#running-handlers-per-language)).

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
- the loopback needs a **runtime shim in the target language** (pure that
  language, speaking the loopback protocol) plus a way to **run the user's
  handler** in that language.

### Running handlers per language

Whether a handler can run in the browser depends entirely on the target
language. Two families:

- **VM / interpreted** — ship the language's VM as WASM (or use the browser's
  own), run the handler and a pure-language shim directly. No compiler needed.
- **Compiled** — the handler has to be compiled first. In-browser compilers for
  these are either enormous or immature, so they are **compile-server** work
  (revive `compilation-queue-server`), not v1 client-side.

| Language | Handler in browser via | Approx. payload | Shim |
|---|---|---|---|
| JavaScript | native | — | pure JS |
| TypeScript | `esbuild-wasm` / `swc` transpile, then run | ~1–3 MB | pure TS |
| Lua 5.4 | `wasmoon` (Lua→WASM) | ~200 KB | pure Lua |
| Luau | emscripten build of Luau | ~1–2 MB | pure Luau |
| Python 3.11+ | Pyodide (CPython→WASM) | ~6–10 MB core | pure Python |
| C | `tcc.wasm` (limited) or `wasm-clang` (~25–30 MB) | small–huge | C→WASM, JS calls exports |
| Rust / C++ / Go | no practical in-browser compiler | — | **compile server** |

Rollout order follows payload and maturity: **JS/TS → Lua → Luau → Python**
client-side; **Rust / C / Go** via the server. The compile/diagnostics/codegen
loop is unaffected — it works for every target from the start.

This is the piece to **research first**: confirm `rust-sitter` /
`tree-sitter-c2rust` build clean for `wasm32-unknown-unknown`; measure the real
Pyodide / wasmoon / Luau-wasm / esbuild-wasm payloads on a warm cache; check
`tcc.wasm`'s language-feature ceiling. The matrix above is the hypothesis, not a
verified result.

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

**SvelteKit for the apps, framework-neutral for what's shared.** The
`playground` and `tutorial` stay SvelteKit (the existing scaffold). Below them:

- a **neutral TS package** — the WASM module + its JS wrapper (`parse`,
  `validate`, `generate`, `runLoopback`), the per-language handler runners
  (Pyodide / wasmoon / esbuild adapters), the loopback "wire" engine, and the
  diagnostics / IR types. No framework. (This is what `web/shared/shared-compile`
  and `shared-compilation` were reaching for.)
- a **Svelte component library** (`shared-components`) for the editor, the
  IR / code / message-flow panels, and the stats graphs — consumed by both
  apps.

For **docs embedding**: the docs site is Zensical (static, no Svelte runtime).
Compile the playground shell as a **custom element** (`<svelte:options
customElement>`) so a guide / tutorial page can `<script src>` it and drop
`<comline-playground schema="...">` inline — no iframe, shares the page's theme.
An iframe of the SvelteKit playground is the fallback if the custom-element path
gets fiddly.

To decide: one deploy or three (docs / playground / tutorial); one domain or
subdomains.

## Decided

- **v1 scope** — everything: compile + diagnostics + codegen + a runtime demo.
- **Framework** — SvelteKit for `playground` and `tutorial`; a neutral TS
  package for the WASM/loopback/runner core; a Svelte component library, also
  built as custom elements for the docs.

## Open questions

- **The `compilation-queue-server`** — it *will* be needed for Rust / C / Go
  handlers (and real `cargo build` of a `lib` crate). Revive it in parallel with
  v1, or ship the VM-language loopback first and add it once those land?
- **Language research** — the [handler matrix](#running-handlers-per-language) is
  a hypothesis. Verify the WASM builds and payloads before committing an order.
- **Tutorial content** — authored inside the `tutorial` app, or as Markdown in
  `docs/` and rendered by both? *(TBD.)*
- **Deploy shape** — one deploy or three; one domain or subdomains.
- **Version sync** — the playground pins `core` / `generation` revs; it inherits
  the same [git-rev treadmill](generation.md#open-questions) until those crates
  cut releases.
