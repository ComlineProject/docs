# Generators

A **generator** turns a compiled schema into source code for a target
language. The CLI doesn't have to link it in: a generator can be its own
program, native or WebAssembly, that speaks a small protocol over stdin and
stdout. The two official generators, Rust and TypeScript, speak the same
protocol. The CLI links them in for speed, but calls them through the same
request and response types, so every `comline generate` exercises it.

The protocol's every field is in the
[generator protocol reference](../../reference/generator-protocol.md). This page
is the walkthrough.

## The shape

1. The CLI asks the generator to **`Describe`** itself: which languages and
   versions it handles, and which protocol versions and IR formats it accepts.
2. It checks the answer, and refuses a generator it doesn't share a protocol
   or IR format with, naming both sides.
3. It sends one **`Generate`** request per target: every schema in the package
   as frozen IR, the mode, the package's name and version, the target
   language and version, and which type implements each encoding.
4. The generator answers with a list of files: a relative path and the
   contents of each.

Each request and each response is one CBOR document. The IR inside a request
is the same encoding `.comline/` stores.

## Write one in Rust

The `comline-codegen` crate (in the
[generation](https://github.com/ComlineProject/generation) repository) holds
the protocol types and `serve_stdio`, a generator process's whole `main`. It
reads one request from stdin, answers it from a `Registry`, and writes the
response.

The official binaries are the model. This is `comline-gen-rust`:

```rust
use std::process::ExitCode;

fn main() -> ExitCode {
    let mut registry = comline_codegen::Registry::new();
    comline_codegen_rust::register(&mut registry);
    comline_codegen::protocol::serve_stdio(&registry)
}
```

`comline-gen-typescript` is the same with the TypeScript generator.

A generator is a function from a `GenerateRequest` to its files, registered with
its language, its file extension, a table of the features it supports and the
language versions it handles. Look at the `comline-codegen-rust` and
`comline-codegen-typescript` crates for a full one.

- `serve_stdio` exits successfully whenever it wrote a response, an error
  response included.
- A request it can't read, a protocol or IR format it doesn't accept, an
  unknown target, a generator that fails, and a generator that panics all come
  back as an error response. Only a failure to read stdin or write stdout
  fails the process.
- A generator should call the encodings check before it renders: every
  encoding the package uses has a mapping in the request, and an unmapped one
  is one sentence naming it and the language
  ([Map it to a type](encodings.md#5-map-it-to-a-type)).

A generator doesn't have to be written in Rust. It needs to read and write
CBOR, and to decode the IR (the frozen units) in the form
`comline-core` defines. The Rust crates are the only reference implementation
today.

## Packaging

| Form | Runs as | Sandboxed |
|---|---|---|
| a `.wasm` file | a WASI module, under wasmtime | yes |
| anything else | a native process, with an empty environment | no |

The official generators build for `wasm32-wasip1` too. The `.wasm` form needs
the CLI's `gen-wasm` feature, which is on by default; a build without it
refuses a `.wasm` generator with a message saying so.

## Use one

Point a target at it in `comline.toml`:

```toml
[[generate.target]]
generator = "tools/comline-gen-go.wasm"   # or a native executable
language  = "go"                          # optional if the generator offers one language
timeout   = 120                           # seconds per call, default 60
```

- **`generator`** is a path, relative to the directory of `comline.toml`.
- **`language`** picks among the languages the generator offers. It can be left
  out if it offers one, and it must still be a language the package's
  `config.idp` declares under `code_generation.languages`.
- **`timeout`** is seconds per call, at least 1. It applies only to an external
  generator, and is an error on a built-in one.
- **`lang_version`** applies as for a built-in.

The CLI refuses a generator whose protocol version or IR format it doesn't
share, and one that doesn't offer the target's language at its version.

## Limits

An external generator is untrusted code, and the CLI runs it that way.

| | `.wasm` | native |
|---|---|---|
| Directories | none preopened | the user's own |
| Environment | none | empty |
| Network | none | the user's own |
| Arguments | only `argv[0]` | none |
| Memory | at most 1 GiB | not limited |
| Time | `timeout` seconds per call | `timeout` seconds per call |

- A generator that writes more than 256 MiB to stdout, or generates more than
  256 MiB of file contents, is refused.
- Its stderr is shown, prefixed with its file name, up to 64 KiB.
- **A native generator isn't sandboxed.** It can do anything the user can. Run
  only executables you trust.

Every path in a response must be relative and normalized: no `..` or `.`
components, no absolute paths, no `\`, no `:` (drive or stream prefixes), no
empty components, no NUL. **A response with any bad path is refused whole**, and
nothing from it is written. The built-ins go through the same checks.

## The playground

The playground can run an external WASI generator as the CLI does. Each call
runs in its own worker that is terminated at the deadline (60 seconds by
default), and a memory cap of 1 GiB is enforced on the module. It asks the
generator to describe itself first and applies the CLI's checks. Nothing in the
playground's interface reaches this yet, so for now it's a capability of its
code, not something a visitor can use.

## Registry

Naming a generator by a registry package, instead of a path, is deferred to the
registry (recorded on
[core#8](https://github.com/ComlineProject/core/issues/8)). Today `generator`
is a path.
