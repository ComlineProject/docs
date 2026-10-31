# Conformance spec

How an encoding is proven: the case format, the protocol an implementation
speaks to be tested, and where the vectors live. The guide to using it is
[Formats and framings](../guide/extending/encodings.md); this is the reference.

The source of truth is the runtime's
[`runtime/conformance/README.md`](https://github.com/ComlineProject/runtime/blob/main/runtime/conformance/README.md)
and the
[`comline-reference` README](https://github.com/ComlineProject/runtime/blob/main/runtime/reference/README.md#the-protocol).
This page summarizes them and links there for the long tables. Where they
differ, they win.

## Version

**Spec version: `0.1`** (`runner::SPEC_VERSION`). It covers the case format
(`vectors/*.json`, `profiles/*.json`), the ops, and the value and type
encodings.

- While Comline is in its early days (0.x), a minor version of the spec may
  change anything, and the change is named in the pull request that makes it.
- The **ops protocol** keeps its own number, `protocol: 1` in a `version` reply.
  Under it, ops and reply fields are only ever added.

## Files

| File | Holds |
|---|---|
| `vectors/<feature>.json` | `{"feature": "<feature>", "cases": [...]}`: one feature's cases |
| `profiles/<name>.json` | one encoding's [profile](../guide/extending/encodings.md#2-write-the-profile) |
| `features.json` | the official wire features and their ids (runtime corpus only) |

**A package's vectors** sit beside its profile: the profile's path with `.json`
replaced by `.vectors.json`. `profiles/lines.json` has
`profiles/lines.vectors.json`. Every case in the file is run, and the profile's
`proven_by` names cases in it. The official encodings keep a `vectors/`
directory in the runtime instead; `comline conformance --corpus <dir>` runs
that layout.

## A case

A case is one operation and the bytes it must produce:

```json
{
  "id": "envelope/err",
  "op": "envelope",
  "input": { "kind": "err", "id": 258, "body": "6669656c6473" },
  "bytes": "0102016669656c6473"
}
```

| Field | Meaning |
|---|---|
| `id` | unique name, `<feature>/<case>`; what a profile's `proven_by` lists |
| `op` | the operation, below |
| `input` | the operation's input |
| `bytes` | the encoded form, lowercase hex |
| `expect` | optional: `"reject"` means decoding `bytes` must fail; the input then names only what selects the decoder (the framing) |
| `compare` | optional: `"json"` compares JSON text as JSON (RFC 8259) instead of byte for byte |

- **Bytes** are lowercase hex.
- **64-bit and wider integers** (`ir_hash`, `request_id`, `u64`, `i64`, `u128`,
  `i128` values) are decimal strings, so a reader that holds JSON numbers as
  doubles keeps them exact.
- A case **encodes and decodes** unless its op says otherwise: encoding the
  input gives exactly `bytes`, and decoding `bytes` gives the input back.

### Ops

| `op` | `input` | Checked |
|---|---|---|
| `name_hash` | `name` | the hash, 8 bytes little-endian |
| `handshake` | `ir_hash`, `wire_format`, `framing` (names, unhashed), `capabilities` | encode and decode |
| `envelope` | `kind`: `ok` with `payload`, `err` with `id` and `body`, or `fault` | encode and decode |
| `request` | `framing`, `call_id`, `method`, `request_id`, `format`, `params`, and `one_way` when `true` | encode and decode |
| `response` | `framing`, `request_id`, and an envelope's fields | encode and decode |
| `encode` | `format`, `value` | encode |
| `decode` | `format`, `type`, `value` | decode: `bytes` read as `type` give `value` |
| `stream_prefix` | `len`, `max` | encode and decode the 4-byte length prefix of a `len`-byte frame under the limit `max` |
| `stream_split` | `max`, `frames`, `rest`, `needed` | encode and decode a byte stream of `frames`, each behind its prefix, then `rest` |

A framing is proven with `request` and `response` cases; a format with `encode`
and `decode` cases.

Values and types are written in a typed encoding (`{"u8": 255}`,
`{"struct": {"name": "Point", "fields": [...]}}`, and so on). The full list is
in the
[runtime README](https://github.com/ComlineProject/runtime/blob/main/runtime/conformance/README.md#the-corpus).

### Stream framing

A frame on a byte stream is `[len: u32 LE][len bytes]`. A runtime refuses a
`len` over its limit, by default 16 MiB (16,777,216 bytes) in every runtime,
and `len == max` is accepted. A transport that carries messages natively has
no prefix. See [Transports](../guide/extending/transports.md).

## How a case is judged

- **A rejection** (`expect: "reject"`) asks to decode its `bytes`, which must
  fail. A `stream_prefix` rejection also asks to encode its input, which must
  fail.
- **Any other case** asks to encode its input (unless it is a `decode`) and to
  decode its `bytes` (unless it is a `name_hash` or an `encode`).
- It **passes** when every encode gives its bytes (compared as JSON for
  `"compare": "json"`), every decode accepts and gives the input back exactly,
  and a rejection is refused.
- An answer of `not_implemented` makes the case not implemented; `error` fails
  it.
- The questions of a case never depend on earlier answers, so they can all be
  asked up front.
- **A profile fact is proven** when every case it names passes and shows its
  value. A format's facts are shown by `decode` cases of the `Point` and `Color`
  shapes the official profiles use.

## The ops protocol

An implementation under test is a process. It reads **one JSON request per
line** on stdin, writes **one reply line each** on stdout, and exits 0 when
stdin ends. A line may also be a JSON array of requests (a batch), answered by
an array in the same order. `comline conformance --impl` and the Rust
`comline-reference` binary both speak it.

A request:

| Field | Meaning |
|---|---|
| `id` | any JSON value; echoed in the reply |
| `op` | a case op, or `check`, `version` or `session` |
| `input` | the op's input, as a case states it |
| `bytes` | optional, lowercase hex |

- **With no `bytes`,** the reply is what `input` encodes to:
  `{"id": 1, "bytes": "0102..."}`.
- **With `bytes`,** the reply says whether they decode:
  `{"id": 2, "accept": true, "input": {...}}` or `{"id": 3, "accept": false}`. A
  refusal carries no reason: what runtimes must agree on is whether bytes are
  refused.
- **`{"id": ..., "not_implemented": "..."}`** means the implementation doesn't
  have a format or framing the request names.
- **`{"id": ..., "error": "..."}`** means the request is malformed. A malformed
  line never stops the process.
- **`decode`** is decode-only, and **`name_hash`** and **`encode`** are
  encode-only.

### `version`

The first thing `comline conformance` asks. The reply says what the
implementation supports:

```json
{"id": 6, "version": {"protocol": 1, "crate": "0.1.0",
   "ops": ["name_hash", "handshake", "envelope", "request", "response", "encode", "decode",
           "stream_prefix", "stream_split", "check", "version", "session"],
   "formats": ["json@1", "msgpack@1", "packed@1"],
   "framings": ["datagram@1", "datagram@2", "jsonrpc@1"]}}
```

`protocol` must be the runner's (`1`), or the CLI refuses the implementation.
`formats` and `framings` list the encodings it implements, namespaced names
included (`com.acme.lines@1`).

### `check` and `session`

`check` asks whether a value is a value of a type, so a fuzzer can validate a
pair before asking about it. `session` drives one side of a connection's sans-IO
state through a list of events, for runtimes that compare their connection
logic with the reference. Neither is needed to test an encoding with
`comline conformance`. Both are in the
[`comline-reference` README](https://github.com/ComlineProject/runtime/blob/main/runtime/reference/README.md#the-protocol).

## The runner as a library

A Rust crate can run the same checks in its own CI by depending on
`comline-runtime-conformance` (`runtime/conformance`) by git rev. Its `runner`
module provides:

- `load_corpus(dir)`, `load_vectors(path)` and `load_profile(path)`;
- `Corpus::cases_for(profile)` and `Corpus::prove(profile, outcomes)`;
- `questions(case)`, `judge(case, answers)` and `byte_diff(got, expected)`;
- the `Implementation` trait, with `InProcess` and `Lines` (any reader and
  writer speaking the ops protocol), and `run_all(cases, implementation)`.

## Running it

```
comline conformance --impl "<command line>" [--encoding <name>]... [--corpus <dir>] [--timeout <secs>]
```

The flags are described in the
[CLI reference](cli.md#commands). The implementation runs under the same rules
as an external generator: a cleared environment, a time limit (60 seconds by
default) and a capped stdout, with its stderr shown. The command line is split
on whitespace, with no shell quoting, and a bare program name is looked up on
`PATH`.

## Not covered

Behavioural features (transports, timeouts, one-way calls) aren't in the corpus:
a vector can't prove them. Whether a one-way call gets a reply frame is
behaviour, not bytes, so no profile states it.
