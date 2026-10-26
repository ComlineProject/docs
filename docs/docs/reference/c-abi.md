# C ABI

The C ABI of `comline-runtime-ffi`: what a language other than Rust binds to
for the `comline@1` handshake, the connection framings (`datagram@2`,
`jsonrpc@1`), envelopes, connection state and frame limits. Codecs,
transports, async and dispatch stay in each host.

- **ABI version 0.1.** It is not frozen; see [Version](#version).
- **Source:** [`runtime/ffi`](https://github.com/ComlineProject/runtime/tree/main/runtime/ffi)
  in the runtime repository.
- **Header:** [`include/comline.h`](https://github.com/ComlineProject/runtime/blob/main/runtime/ffi/include/comline.h).
  cbindgen 0.29.2 generates it from `src/lib.rs`, and it is checked in. Its
  comments are the doc comments of the Rust source.
- **Why it exists and what was decided:** [one protocol core](../proposals/shared-runtime-core/core-interface.md).

This page was written against runtime `main` at `cb41d31`. Where it and the
header disagree, the header is right.

## Version

- The header defines `COMLINE_ABI_MAJOR` (0) and `COMLINE_ABI_MINOR` (1).
- `comline_abi_version()` returns the library's, as `(major << 16) | minor`.
- **A host checks it at load, before any other call.**

  ```c
  if (comline_abi_version() != ((COMLINE_ABI_MAJOR << 16) | COMLINE_ABI_MINOR)) {
      /* refuse the library, naming both versions */
  }
  ```

- **Before 1.0, a minor counts as a major.** A host built against `0.1` accepts
  only `0.1`. The JS glue does exactly this.
- The major changes when a signature, a struct layout or the meaning of a code
  changes. The minor changes when functions, codes or flag bits are added.
- Structs are frozen within a major. New data comes through new functions or new
  flag bits.
- Status codes, event kinds and flag bits are append-only. A host maps a code
  it doesn't know to a generic error carrying the number.
- `comline_supports(name, len)` says whether this build carries a framing or
  handshake by name, so a host can refuse a schema's `@framing` at setup, not
  at the first frame.

## A connection's life

1. `comline_connection_new` with a [`comline_config`](#comline_config).
2. `comline_connection_start` writes this side's handshake frame. Send it
   first.
3. `comline_connection_feed` with what arrives. The first frame is the peer's
   handshake and gives `COMLINE_EVENT_HANDSHAKE_OK`. It may arrive before or
   after `start`. A request or reply needs both.
4. Calls and replies: `comline_connection_encode_request`,
   `comline_connection_feed`, `comline_connection_encode_reply`. When the
   host's clock says a call timed out, `comline_connection_abandon`.
5. `comline_connection_free`.

With `COMLINE_HANDSHAKE_NONE` there is nothing to send or check: the
connection is open from the start, and `start` writes nothing.

## Status codes

`comline_status` is an `int32_t`. Below 16 is an outcome, 16 and up is an error.

| Code | Value | Meaning |
|---|---|---|
| `COMLINE_OK` | 0 | Done. |
| `COMLINE_NEED_MORE` | 1 | Stream mode: no whole frame in the input yet. Nothing was consumed. `ev->frame.len` is the total bytes the frame takes, prefix included, once the prefix is complete (0 before that). |
| `COMLINE_BUFFER_TOO_SMALL` | 2 | The output didn't fit `cap`. `*written` is the exact size needed, and nothing changed: no request id spent, nothing waits. |
| `COMLINE_ERR_FRAMING` | 16 | A malformed frame, or (ordered connections) a reply that skips the innermost waiting call. The frame was consumed and the connection stays usable. |
| `COMLINE_ERR_HANDSHAKE` | 17 | The peer's `comline@1` frame didn't parse, or names another schema, wire format or framing. The connection is closed. |
| `COMLINE_ERR_FRAME_TOO_LARGE` | 18 | A frame over `max_frame`. See [Frame limits](#frame-limits). |
| `COMLINE_ERR_UNKNOWN_FRAMING` | 19 | A framing name this library has no connection form of. |
| `COMLINE_ERR_INVALID_ARGUMENT` | 20 | A null pointer where one isn't allowed, a name that isn't UTF-8, a field outside its values, buffers that overlap, or a length over `isize::MAX`. |
| `COMLINE_ERR_STATE` | 21 | The call doesn't fit the connection's state: a request or reply before the handshake completed, a second `start`, or any call on a closed connection. |
| `COMLINE_ERR_POISONED` | 22 | An earlier call on this handle panicked. Drop the handle. |
| `COMLINE_ERR_BUSY` | 23 | The request wasn't made: `max_waiting` calls already wait. Nothing written, no request id spent. Queueing is the host's choice. |

Every call that takes a handle can also return `COMLINE_ERR_INVALID_ARGUMENT`
(a null handle or pointer), `COMLINE_ERR_POISONED`, and `COMLINE_ERR_STATE` on a
closed connection. The tables below list only what is particular to a call.

## Constants

| Constant | Value | Meaning |
|---|---|---|
| `COMLINE_DEFAULT_MAX_FRAME` | 16 MiB | The frame limit when `max_frame` is 0, prefix not counted. |
| `COMLINE_MAX_FRAME_CEILING` | 4294967291 | The most `max_frame` can be: `u32::MAX` less the prefix. |
| `COMLINE_PREFIX_LEN` | 4 | A stream's length prefix: a `u32`, little-endian. |
| `COMLINE_HANDSHAKE_LEN` | 31 | The `comline@1` frame. |
| `COMLINE_HANDSHAKE_COMLINE` / `_NONE` | 0 / 1 | `comline_config.handshake`. |
| `COMLINE_ENVELOPE_OK` / `_ERR` / `_FAULT` | 0 / 1 / 2 | A reply's outcome. |

## Structs

### `comline_config`

Read once by `comline_connection_new`. The name pointers are borrowed for that
call. Zero every field you don't set, including `_reserved`.

| Field | Type | Meaning |
|---|---|---|
| `ir_hash` | `uint64_t` | The schema fingerprint the generated code was built from. Only the handshake reads it. |
| `wire_format`, `wire_format_len` | `const uint8_t *`, `size_t` | The wire format's name (`"packed@1"`), UTF-8, not NUL-terminated. The codecs are the host's, so any name is taken; only the handshake reads it, hashed. |
| `framing`, `framing_len` | `const uint8_t *`, `size_t` | `"datagram@2"` or `"jsonrpc@1"`. UTF-8, not NUL-terminated. |
| `max_frame` | `uint64_t` | The largest frame sent or taken, prefix not counted. 0 is the default. Above `COMLINE_MAX_FRAME_CEILING` is `COMLINE_ERR_INVALID_ARGUMENT`. |
| `capabilities` | `uint32_t` | Transport capability bits, sent in the handshake. Advisory: peers that differ still agree. |
| `max_waiting` | `uint32_t` | How many calls may wait for a reply at once. The room is reserved when the handle is made. 0 is none: the connection serves requests and sends one-way calls only. |
| `handshake` | `uint8_t` | `COMLINE_HANDSHAKE_COMLINE` or `COMLINE_HANDSHAKE_NONE`. |
| `stream` | `uint8_t` | 1: a byte stream, each frame behind a `u32` LE length prefix (TCP, a pipe, stdio). 0: one frame per message, boundaries kept by the transport (WebSocket, UDP). |
| `unordered` | `uint8_t` | 1: replies may come in any order (a host with several calls in flight). 0: calls nest, and a reply must answer the innermost waiting call. |
| `_reserved` | `uint8_t` | Must be 0. |

`stream` and `unordered` take 0 or 1; any other value is
`COMLINE_ERR_INVALID_ARGUMENT`. The struct is 64 bytes on a 64-bit target and 48
on wasm32, because it holds pointers.

### `comline_span`

`{ uint32_t offset; uint32_t len; }`: a part of the input, `offset` bytes from
its start. 8 bytes.

### `comline_event`

What one fed frame means. 48 bytes, aligned to 8. A field that isn't valid for
the kind and flags is 0.

| Offset | Field | Type | Valid for |
|---|---|---|---|
| 0 | `kind` | `uint8_t` | always: `COMLINE_EVENT_*` |
| 1 | `flags` | `uint8_t` | always: see the flags below |
| 2 | `protocol` | `uint16_t` | a request with `HAS_PROTOCOL` |
| 4 | `call_id` | `uint16_t` | a request without `CALL_BY_NAME` |
| 6 | `envelope` | `uint8_t` | a reply: `COMLINE_ENVELOPE_*` |
| 7 | `_reserved` | `uint8_t` | |
| 8 | `error_id` | `uint16_t` | a reply with `COMLINE_ENVELOPE_ERR`: the schema-global ordinal |
| 10 | `_reserved2` | `uint16_t` | |
| 12 | `call_name` | `comline_span` | a request with `CALL_BY_NAME` |
| 20 | `body` | `comline_span` | a request's params, or a reply's result or error body |
| 28 | `frame` | `comline_span` | every frame: the whole frame, prefix not included |
| 36 | `capabilities` | `uint32_t` | `HANDSHAKE_OK`: the peer's capability bits |
| 40 | `request_id` | `uint64_t` | a request's id (0 for a one-way `jsonrpc@1` request), to answer it with; or the id of the call a reply answers |

Event kinds:

| Kind | Value | Meaning |
|---|---|---|
| `COMLINE_EVENT_HANDSHAKE_OK` | 0 | The peer's handshake arrived and agrees with ours. |
| `COMLINE_EVENT_REQUEST` | 1 | The peer calls this side. |
| `COMLINE_EVENT_REPLY` | 2 | The reply to a call this side waits on, which no longer waits. |
| `COMLINE_EVENT_STALE` | 3 | A reply to a call nobody waits on any more (it was abandoned). Drop it. |

Flags:

| Flag | Bit | Meaning |
|---|---|---|
| `COMLINE_EVENT_HAS_PROTOCOL` | `1 << 0` | `protocol` holds the protocol the request is for. Set on `datagram@2` requests. A `jsonrpc@1` request names only its method. |
| `COMLINE_EVENT_ONE_WAY` | `1 << 1` | The request wants no reply. Set whenever the frame says so (a `jsonrpc@1` notification), never inferred from a request id of 0. `datagram@2` can't say it, so there the schema tells one-way calls apart. |
| `COMLINE_EVENT_CALL_BY_NAME` | `1 << 2` | The request names its call by `call_name`, not `call_id`. |
| `COMLINE_EVENT_BODY_ABSENT` | `1 << 3` | The frame has no body: JSON-RPC `params`, `result` or `error.data` absent or `null`. `body` is empty, and a JSON codec reads it as `null`. |
| `COMLINE_EVENT_NAME_ESCAPED` | `1 << 4` | `call_name` is JSON string text with escapes in it, as the frame spelled it (`app.Chat\/count`). Read it with `comline_method_name_unescape`, or compare it as JSON text. |

### `comline_handshake`

A decoded `comline@1` frame, written by `comline_handshake_check`. 32 bytes.

| Field | Type | Meaning |
|---|---|---|
| `ir_hash` | `uint64_t` | The peer's schema fingerprint. |
| `wire_format` | `uint64_t` | The wire format's name, hashed (`comline_name_hash`). |
| `framing` | `uint64_t` | The framing's name, hashed. |
| `capabilities` | `uint32_t` | The peer's capability bits. |
| `_reserved` | `uint32_t` | 0. |

## Functions

### Connection

| Function | Purpose | Errors |
|---|---|---|
| `comline_connection_new(cfg, &out)` | Make a connection into `*out`. The one allocation the library makes: the handle, with room for `max_waiting` waiting calls. | `INVALID_ARGUMENT` (a null pointer, a name that isn't UTF-8, a field outside its values, `max_frame` above the ceiling, `*out` overlapping the config or its names), `UNKNOWN_FRAMING`. `*out` is null on any error, or left as it was if it overlaps an input. |
| `comline_connection_free(conn)` | Free it. Null is a no-op. Works on a poisoned or closed handle. | none |
| `comline_connection_start(conn, out, cap, &written)` | Write this side's handshake frame, with its prefix in stream mode. Without a handshake it writes nothing. | `BUFFER_TOO_SMALL` (`*written` is 31, or 35 in stream mode), `FRAME_TOO_LARGE` (`max_frame` below 31), `STATE` (already written). |
| `comline_connection_feed(conn, in, in_len, &consumed, &ev)` | Feed received bytes and get the event for the next frame. One frame per call. | `NEED_MORE`, `FRAMING`, `HANDSHAKE` (closes the connection), `FRAME_TOO_LARGE`. |
| `comline_connection_encode_request(conn, protocol, call_id, name, name_len, expects_reply, body, body_len, out, cap, &written, &request_id)` | Frame a request around a body the host's codec already wrote. `*request_id` is the id it was given. `expects_reply` is 1 for a call that waits, 0 for a one-way call. | `BUFFER_TOO_SMALL`, `FRAME_TOO_LARGE`, `BUSY`, `INVALID_ARGUMENT` (a name that isn't UTF-8, `expects_reply` not 0 or 1), `STATE` (handshake not complete). None of them spends a request id or leaves a call waiting. |
| `comline_connection_encode_reply(conn, protocol, request_id, envelope, error_id, body, body_len, out, cap, &written)` | Frame the reply to a request this side was given. | `BUFFER_TOO_SMALL`, `FRAME_TOO_LARGE`, `INVALID_ARGUMENT` (a `FAULT` with a body, an unknown envelope), `STATE` (handshake not complete). |
| `comline_connection_abandon(conn, request_id)` | Stop waiting on a call that timed out. A late reply to it is `STALE`. An id nobody waits on is a no-op. | none |
| `comline_connection_is_waiting(conn, &waiting)` | `*waiting` is 1 if any call waits for a reply, else 0. | none |

### Without a handle

These are pure and re-entrant.

| Function | Purpose | Errors |
|---|---|---|
| `comline_abi_version()` | The ABI version: the major in the high 16 bits, the minor in the low 16. | none |
| `comline_supports(name, len)` | 1 if this build carries the named framing or handshake: `datagram@2`, `jsonrpc@1`, `comline@1`, `none`. 0 otherwise, `datagram@1` and wire formats included. | none |
| `comline_name_hash(name, len, &hash)` | The FNV-1a-64 hash of an encoding name, as the handshake carries it. | `INVALID_ARGUMENT` |
| `comline_handshake_encode(ir_hash, wire_format, wire_format_len, framing, framing_len, capabilities, out, cap, &written)` | Write a 31-byte `comline@1` frame with no prefix, for a host that runs the handshake itself. Any UTF-8 name is taken. | `BUFFER_TOO_SMALL` (`*written` is 31), `INVALID_ARGUMENT` |
| `comline_handshake_check(ours, ours_len, peer, peer_len, peer_out)` | Check a peer's frame against ours. They must agree on schema, wire format and framing; capability bits may differ. `*peer_out`, unless null, gets the peer's frame whenever it parses, so a host can say what the peer declared. Bytes after the 31-byte frame are ignored ([runtime#33](https://github.com/ComlineProject/runtime/issues/33)). | `HANDSHAKE` (they disagree, or `peer` doesn't parse), `INVALID_ARGUMENT` (`ours` doesn't parse) |
| `comline_method_name_unescape(in, len, out, cap, &written)` | Turn a `call_name` span with `NAME_ESCAPED` into UTF-8. Text with no escapes is copied as it is. | `BUFFER_TOO_SMALL` (`*written` is the exact size, nothing written), `INVALID_ARGUMENT` (not a valid JSON string's text) |

## What each framing reads

A connection always speaks a connection framing, whose frames say whether they
are a request or a reply. `datagram@1` is lockstep and has no connection form:
`comline_connection_new` returns `COMLINE_ERR_UNKNOWN_FRAMING` for it.

| | `datagram@2` | `jsonrpc@1` |
|---|---|---|
| `encode_request` reads | `protocol` and `call_id`; `name` is ignored | `name`, escaped as serde_json escapes a string; `protocol` and `call_id` are ignored |
| A one-way request out | Looks like any other: the frame can't say it | A notification, with no `id` |
| An empty body is written as | nothing | `null` |
| `feed` of a request gives | `HAS_PROTOCOL`, `protocol`, `call_id`, `request_id` | `CALL_BY_NAME`, `call_name` (with `NAME_ESCAPED` if it has escapes), `request_id` |
| A one-way request in | not marked | A notification: `ONE_WAY`, `request_id` 0 |
| `encode_reply` writes | `protocol` and the request id | the id; `protocol` is ignored. An error is a JSON-RPC `error` object with `code` set to `error_id`; a fault is `-32603` |
| `BODY_ABSENT` | never | `params`, `result` or `error.data` absent or `null` |

`name` is any UTF-8 text. It may be empty for `datagram@2`.

## Frame limits

`max_frame` is the connection's limit, in bytes, not counting a stream's
prefix. It may be lowered, or raised up to `COMLINE_MAX_FRAME_CEILING`.

| Case | Result |
|---|---|
| An encode over the limit | `COMLINE_ERR_FRAME_TOO_LARGE`. Nothing written, no request id spent, the connection keeps working. |
| `feed`, stream mode, a prefix over the limit | `COMLINE_ERR_FRAME_TOO_LARGE`. The stream can't be resynchronised, so the connection is closed and later calls return `COMLINE_ERR_STATE`. |
| `feed`, message mode, a frame over the limit | `COMLINE_ERR_FRAME_TOO_LARGE`. The frame is refused and the connection keeps working. |

`encode_reply` returns `FRAME_TOO_LARGE` for a reply over the limit and leaves
the connection usable. The Rust drivers answer such a reply with a fault; the
ABI leaves that to the host.

## Rules every function keeps

- **One crossing per frame.** `feed`, `encode_request` and `encode_reply` each
  handle one whole frame. Nothing calls back into the host.
- **Buffers are the caller's.** Every output goes to an `out`, `cap`,
  `*written` triple. Every input is borrowed for the call only. The library
  never frees host memory and the host never frees library memory.
- **Spans are offsets, not pointers.** They count from the start of the input
  passed to the `feed` that produced them, so they stay valid if the host
  moves its buffer afterwards. They fit a `u32` under the frame ceiling.
  Nothing is copied out of the input.
- **No allocation after `comline_connection_new`.** The handle is the one
  thing the library allocates. The exemption is `jsonrpc@1` decoding, which
  allocates through serde_json when it refuses a frame, when a member name has
  an escape, and when a value nests brackets three deep (`"params":[[1]]`). It
  is [runtime#58](https://github.com/ComlineProject/runtime/issues/58), deferred.
  Every `datagram@2` feed and every encode, under either framing, allocates
  nothing.
- **Null pointers.** A data pointer may be null only when its length or
  capacity is 0. A length or capacity over `isize::MAX` is
  `COMLINE_ERR_INVALID_ARGUMENT`.
- **Inputs and outputs must not overlap.** No buffer a call writes (`out`,
  `*written`, `*ev`, the handle) may share a byte with any buffer or
  out-pointer the same call takes. A call given overlapping ones returns
  `COMLINE_ERR_INVALID_ARGUMENT` and touches nothing. Inputs may overlap each
  other.
- **Panics never cross.** Every function runs inside `catch_unwind`. A panic is
  a bug. The call returns `COMLINE_ERR_POISONED`, the handle is poisoned and
  every later call on it returns the same, so the host drops the connection.
  `comline_connection_free` still works. A free function returns
  `COMLINE_ERR_POISONED` for the call that panicked.
- **Threads.** A handle may move between threads, but calls on one handle must
  not overlap: the host locks it. Different handles are independent.
- **Refusals change nothing.** `BUFFER_TOO_SMALL`, `BUSY` and `FRAME_TOO_LARGE`
  on an encode spend no request id and leave no call waiting. After
  `BUFFER_TOO_SMALL`, retry with exactly `*written` bytes of room.
- **A closed connection** (a refused handshake, or an oversized stream prefix)
  answers every call but `comline_connection_free` with `COMLINE_ERR_STATE`.

The layouts of `comline_span`, `comline_event`, `comline_handshake` and
`comline_config` are asserted at compile time in `src/lib.rs`.

## wasm32 and the JS glue

The crate builds for `wasm32-unknown-unknown`, and the same `extern "C"`
functions are the module's exports. There is no `wasm-bindgen`: the `.wasm` is
the C ABI, so a non-JS WebAssembly host (wazero, wasmtime) calls the same
functions with the same meaning.

```sh
cargo build -p comline-runtime-ffi --release --target wasm32-unknown-unknown
```

- **Layouts.** A pointer and `size_t` are 4 bytes, so `comline_config` is 48
  bytes. `comline_event` and `comline_handshake` don't change.
- **Two extra exports,** not in the header, on wasm32 without the `atomics`
  feature:
  - `comline_wasm_reserve_in(len)` and `comline_wasm_reserve_out(len)` return a
    pointer to a region of at least `len` bytes that the module owns, or null if
    memory can't grow.
  - A host copies input into the `in` region and reads output from the `out`
    region.
  - Reserving more may move a region and grow memory, which detaches the host's
    views. Take the pointer again after each reserve.
- **A panic is a trap.** The host discards the instance.

[`js/comline.mjs`](https://github.com/ComlineProject/runtime/blob/main/runtime/ffi/js/comline.mjs)
and [`comline.d.mts`](https://github.com/ComlineProject/runtime/blob/main/runtime/ffi/js/comline.d.mts)
are a hand-written ES module over that build, with no dependencies.

- **Thin.** Every method is one ABI call. It returns the status with whatever
  the call wrote, retries nothing, never throws because of a status and keeps no
  state of its own. A binding builds on it.
- **`instantiate(source)`** compiles the module, checks that its ABI version is
  exactly the glue's, and feeds one `datagram@2` request through to check the
  `comline_event` layout.
- **Memory.** Each call reserves its regions, copies inputs in and copies
  outputs back, so a byte output is a fresh copy and nothing returned points
  into wasm memory. A span is an offset into the array the host fed, so the
  host reads a body from its own array.
- **Types.** A `u64` is a `BigInt` both ways. A name is a string, encoded as
  UTF-8, or a `Uint8Array` of the bytes as they are.
- **A panic** is thrown as a `WebAssembly.RuntimeError`. The glue doesn't catch
  it.

```js
import { instantiate, Handshake } from "./comline.mjs";

const comline = await instantiate(await readFile("comline_runtime_ffi.wasm"));
const { status, connection } = comline.connectionNew({
  framing: "datagram@2",
  handshake: Handshake.NONE,
  maxWaiting: 16,
});
```

## Building natively

```sh
cargo build -p comline-runtime-ffi --release
```

This writes `libcomline_runtime_ffi.so` (a `cdylib`) and `libcomline_runtime_ffi.a`
(a `staticlib`) under `target/release/`. Linking the static library on Linux
needs what a Rust `staticlib` needs from the system: `-lgcc_s -lutil -lrt
-lpthread -lm -ldl -lc`.

To regenerate the header, from `runtime/ffi`:

```sh
cargo install cbindgen --version 0.29.2 --locked
cbindgen --config cbindgen.toml --output include/comline.h
```

## How it is verified

- **The conformance vectors, from three hosts, on the same cases.** Rust
  (`tests/vectors.rs`, through the `extern "C"` functions only), C
  (`tests/c/vectors.c`, C11 against `comline.h`) and Node (`js/test/vectors.test.mjs`,
  against the wasm32 build). C runs against the static library, the dynamic
  library, and the static library under ASan and UBSan.
  - The cases are every one in `name-hash` (8), `handshake` (9), `envelope`
    (8), `framing-datagram` (9), `framing-datagram2` (12) and `framing-jsonrpc`
    (19): 65 in all. Each harness fails on any mismatch, and on a case count
    that differs from the vectors'.
  - The nine `datagram@1` cases have no connection form. For them the harness
    checks that the ABI refuses `datagram@1`.
  - C and Node have no codec, so `examples/export_vectors.rs` writes the cases
    out with their params already encoded.
- **The ABI against the core, on random sequences.** `tests/differential.rs`
  runs random configs and sequences (calls, replies, abandons, peer frames,
  chunked deliveries, flipped bytes) through a `comline_connection` and through
  `State` and the framings directly. They must give the same frames, events and
  refusals. Every call is also held to the rules above. The nightly run uses
  100,000 cases.
- **Fuzz.** `ffi_feed` checks the rules alone; `ffi_vs_core` also compares with
  the core. Both share their driver with the proptest.
- **Miri.** The ABI's tests run under Miri, which checks aliasing, bounds and
  leaks at the `extern "C"` boundary.
- **Header drift.** CI regenerates `comline.h` with the pinned cbindgen and
  fails on any difference.
- **Benchmarks.** Instruction counts of each call, below.

The CI jobs are `ffi`, `ffi miri`, `wasm32 core` and `fuzz (ffi_feed)`,
`fuzz (ffi_vs_core)` and `fuzz (stream_split)`; all are required to merge. See
[Verification](../proposals/shared-runtime-core/verification.md) for how the
fuzz targets and the benchmark gate work, and [Branch rules](../conduct/branch-rules.md).

## What crossing costs

The ABI's benches count instructions (Callgrind, through `iai-callgrind`) for
each call through its `extern "C"` function (`ffi/abi/...`) and for the same
work on `State` and the framings directly (`ffi/core/...`). The difference is
what crossing the boundary costs.

These numbers are from the latest published `rust.bench.json` on the runtime's
[`reports`](https://github.com/ComlineProject/runtime/tree/reports) branch, which
has the `ffi/*` ids: main at `cb41d31`, the merge of
[runtime#60](https://github.com/ComlineProject/runtime/pull/60), built with
rustc 1.98.0. Message mode, a 16-byte payload:

| Call | Core | ABI | Crossing |
|---|---:|---:|---:|
| `feed`, `datagram@2` | 141 | 294 | +153 |
| `feed`, `jsonrpc@1` | 1,550 | 1,703 | +153 |
| `encode_request`, `datagram@2` | 336 | 724 | +388 |
| `encode_request`, `jsonrpc@1` | 518 | 906 | +388 |
| `encode_reply`, `datagram@2` | 320 | 462 | +142 |
| `encode_reply`, `jsonrpc@1` | 331 | 473 | +142 |
| `name_hash` | 49 | 198 | +149 |
| `handshake_encode` | 437 | 772 | +335 |
| `handshake_check` | 100 | 138 | +38 |
| `handshake_check` with `peer_out` | 130 | 210 | +80 |

- **The crossing is a constant per call, not per byte.** `feed` costs the same
  extra at 16 B, 256 B, 4 KiB and 64 KiB. The two encode calls cost 48 more at
  64 KiB (436 and 190).
- **Stream mode** adds a few instructions to the core side and changes the
  crossing little: `feed` +149, `encode_request` +388, `encode_reply` +141 at
  16 B.
- **`jsonrpc@1` decoding is its own cost.** It scans the frame with serde_json
  at about 2.8 instructions a byte (185,825 for 64 KiB, on the core). The
  crossing adds the same 153 on top.
- **runtime#60 cut it.** The overlap check was most of `encode_request`'s
  crossing. From the PR's body, measured locally at the same paths:
  `encode_request` `datagram@2` 965 to 742, `feed` `datagram@2` 319–327 to
  294–299, `handshake_check` 152 to 138. No call got dearer. Counts move by a
  few instructions between machines, because the overlap check compares
  addresses, so the CI figures above differ slightly from the PR's.
- **Not measured:** the wasm32 build and the JS glue. A JavaScript call into
  WebAssembly and the copies in and out are the cost [stage 4](../proposals/shared-runtime-core/index.md#stages)
  has to measure before moving TypeScript.

The gate compares each call with its base on every pull request and fails at
a 1% rise, like the core's benches. Both sides of each pair are gated.

## Not here yet

- **`comline_connection_size` and `comline_connection_init`,** for a host that
  supplies the handle's memory. After 1.0.
- **`comline@2`'s negotiation** hands protocol numbers out at the handshake and
  may change the event struct. If it does, it lands before 1.0 freezes the ABI.
- **Bindings.** No language binds the ABI yet; the JS glue is the only host
  code, and it is a thin wrapper, not a binding.
