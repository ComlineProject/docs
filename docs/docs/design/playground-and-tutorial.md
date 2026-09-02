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

**The target is everything** — compile + diagnostics + codegen + a working
runtime demo; there is no cut-down "just the editor" first release. The
compile/codegen loop is language-agnostic from the outset (it is `core` +
`comline-codelib-gen` in WASM); the *runtime demo* fills in per language by how
runnable that language is in a browser (see
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
  runtime demo. The editor / diagnostics / codegen experience does not depend
  on it.

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
  (revive `compilation-queue-server`), not client-side.

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

This is the piece to **research first**. The `core` side is
[settled](#findings-so-far): it builds for wasm32 and the bundle is ~163 KB
gzipped. What's left is the **handlers** — measure the real Pyodide / wasmoon /
Luau-wasm / esbuild-wasm payloads on a warm cache and check `tcc.wasm`'s
language-feature ceiling. The matrix above is the hypothesis, not a verified
result.

## The "same as the CLI" contract

- One `comline-playground` crate (in `web/` or `generation`) depends on
  `comline-core` + `comline-codelib-gen` and exposes a small `wasm-bindgen`
  surface: compile, then `generate(target, mode)`.
- **Entry point: `comline_core::package::build::PackageSources`** (core#42) — the
  filesystem-free twin of `compile_package`. `.config(src)` (optional; a minimal
  congregation is synthesised) + `.schema(namespace_segments, src)` per editor
  tab + `.compile() -> ProjectContext`. Same interpretation + validation pass as
  the CLI, so diagnostics and IR match.
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

## Near-term: the language server

`ComlineProject/language-server` (`comline-lsp`, `tower-lsp` + `comline-core`)
gives the same edit → parse → diagnostics loop **in a real editor today**, no
WASM or SvelteKit needed — the faster manual-test vehicle while the playground
comes together. It parses `.ids` with `comline-core`'s grammar and provides
diagnostics, an outline, hover, go-to-definition and find-references; completion,
rename, formatting and semantic-tokens handlers exist but aren't all wired into
`backend.rs` yet.

Revived against current `core` and pinned by git rev like the rest of the tree
(language-server#1); it shares `comline-core` with the eventual WASM path, so
work on the analysis layer benefits both.

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

- **Target** — everything: compile + diagnostics + codegen + a runtime demo. No
  cut-down first release; the runtime demo simply fills in per language.
- **Framework** — SvelteKit for `playground` and `tutorial`; a neutral TS
  package for the WASM/loopback/runner core; a Svelte component library, also
  built as custom elements for the docs.

## Findings so far

**`comline-core` + `comline-codelib-gen` build for `wasm32-unknown-unknown` and
the bundle is small** — verified end to end:

- The normal dependency tree is C-free and browser-safe: `rust-sitter` →
  `tree-sitter-c2rust` (pure Rust), no `tokio` / `libloading` / `abi_stable`.
- `comline-core`'s `build.rs` (via `rust-sitter-tool` 0.4.5) already targets
  wasm32 — it writes a minimal `wasm-sysroot` (`stdint.h` / `stdlib.h` /
  `stdio.h` / `stdbool.h`) so the generated tree-sitter `parser.c`
  cross-compiles. The one build requirement is **`clang`** for that C step
  (trivial in CI).
- A `cdylib` size probe — `opt-level = "z"` + LTO + `strip` + `panic = "abort"`,
  exercising **parse → IR → validate → diagnostics → codegen** (rust + ts, code
  + lib) for **both** grammars (IDL and `config.idp`):

  | | raw | gzip | xz |
  |---|---|---|---|
  | probe `.wasm` | 527 KB | **163 KB** | 128 KB |

  Valid MVP module (no SIMD / bulk-memory). `code` 383 KB, `data` 135 KB
  (parser tables + regex DFAs + literals). The tree-sitter-c2rust tables are
  compact — the size worry did not materialise.
- **Not yet in the number:** `wasm-bindgen` glue + data marshalling (tens of KB),
  `wasm-opt -Oz` (would take ~10–20 % off), and project-aware multi-schema
  interpretation. None change the order of magnitude.

`std::fs` / `glob` paths (reading `config.idp`, schema files) *compile* on wasm32
but error at runtime — **resolved by `PackageSources`** (core#42), the
filesystem-free entry that takes the config + schema sources as strings and runs
the same interpretation pass as `compile_package`.

## Open questions

- **The `compilation-queue-server`** — it *will* be needed for Rust / C / Go
  handlers (and real `cargo build` of a `lib` crate). Revive it alongside the
  WASM work, or ship the VM-language loopback first and add it once those land?
- **Language research** — the [handler matrix](#running-handlers-per-language) is
  a hypothesis. Verify each VM's WASM build and payload before committing an
  order.
- **Tutorial content** — authored inside the `tutorial` app, or as Markdown in
  `docs/` and rendered by both? *(TBD.)*
- **Deploy shape** — one deploy or three; one domain or subdomains.
- **Version sync** — the playground pins `core` / `generation` revs; it inherits
  the same [git-rev treadmill](generation.md#open-questions) until those crates
  cut releases.
