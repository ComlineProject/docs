# One protocol core: a C ABI and WASM from one crate

Status: **under discussion** · part of [Shared runtime core](index.md) · stage 2

**The question:** what exactly the shared core owns, and what its boundary
looks like, so that ten or more languages can bind it with no loss of
correctness, conformance or performance.

The constraint this page answers to, as the user set it on 2026-10-25:

> lets presume that comline in the future will have a lot of languages to be
> supported, possibly 10+, so nothing like correctness, conformance,
> performance and so on can be lost, there is in no moment that accepting
> lowering any standard will be possible to accept

So every choice below is judged on all three at once. Where a host makes a
cost unavoidable, the page says so, and the
[stage 1 gates](verification.md) decide by measurement.

## Where things stand

The core already exists. It is `runtime/core` (crate `comline-runtime`) in
`ComlineProject/runtime`, and most of what a shared core needs is already
sans-IO, `no_std` and allocation-free.

**Features** (`runtime/core/Cargo.toml`): `contract` and `packed@1` need only
`serde`'s core traits. `alloc` adds the connection state, client and server.
`std` adds JSON, MessagePack, the in-memory and TCP transports, JSON-RPC and
`package_abi`. `async` and `tokio` add the async driver.

| Piece | Where | Tier | I/O |
|---|---|---|---|
| Handshake frame: encode, decode, check; `name_hash` (FNV-1a-64) | `contract/handshake.rs` (190) | `no_std`, no alloc | none |
| `Envelope` (`Ok` / `Err{id}` / `Fault`, tag byte) | `contract/envelope.rs` (121) | `no_std`, no alloc | none |
| `datagram@1` | `contract/framing.rs` (208) | `no_std`, no alloc | none |
| `datagram@2` (kind byte, protocol varint) | `contract/connection_framing.rs` (255) | `no_std`, no alloc | none |
| `BufMut`, `SliceBuf` (a fixed buffer that records overflow) | `contract/buf.rs` (80) | `no_std`, no alloc | none |
| `RuntimeError` | `contract/error.rs` (56) | `no_std`, no alloc | none |
| `jsonrpc@1` | `framing.rs` (351) | **`std`** (`serde_json` with `RawValue`) | none |
| Connection `State`: request ids, waiting stack, frame → `Event::{Request, Reply, Stale}` | `connection.rs`, lines 44–176 | `alloc` (`waiting: Vec<u64>`) | none |
| `ComlineHandshake` (the exchange) | `handshake.rs` (144) | `alloc` | **`Transport`-bound** |
| Blocking `Connection`, `Client`, `Server` | `connection.rs`, `client.rs`, `serve.rs` | `alloc` | **`Transport`-bound** |
| `AsyncConnection` | `async_connection.rs` (918) | `std` + `futures` | **async** |
| `InMemory`, `Tcp` (`u32` LE length prefix, `MAX_FRAME` 16 MiB) | `transport.rs` (226) | `std` | **I/O** |
| Tokio `Tcp` (same prefix, `MAX_FRAME` declared again) | `async_connection.rs` | `tokio` | **I/O** |
| `package_abi` (`abi_stable` + `libloading`) | `package_abi/` | `std` | n/a |

What this shows:

- **The protocol logic is already sans-IO.** `State`'s own doc says it: "No
  I/O: bytes in, `Event`s out". The blocking and async drivers share it.
  Everything host-bound (transports, the handshake exchange, both drivers,
  timers) sits on top and is not part of the proposal.
- **Four things stop it from being bound as it is:**
  - Framing `encode_request` is generic over `P: Serialize` and
    `W: WireFormat`. A C caller has bytes, not a `Serialize` value.
  - `Call::name` is `&'static str`. A binding's names live in the host.
  - `jsonrpc@1` sits behind `std`, for module organisation and not a real
    need, and it allocates per encode (`u64_bytes` goes through
    `to_string`).
  - Byte-level limits are per transport. `MAX_FRAME` is declared twice in
    Rust, and other languages pick their own.

**The simulator is the working precedent**
(`ComlineProject/simulator`, `Cargo.toml`):

- It pins `comline-runtime` at `rev = "6a208d78…"` with
  `default-features = false, features = ["alloc"]`. The comment says why:
  "`std` pulls `libloading` (dylib) which won't build for wasm32."
- It uses `contract` (the handshake, envelopes and both datagram framings)
  and `format::Packed`, and builds to `wasm32-unknown-unknown` with
  `wasm-bindgen` (`scripts/build-wasm.sh`).
- It hits three of the four gaps above and works around each one:
  - **`Preencoded`** (`src/format.rs`) is a `WireFormat` whose `encode`
    ignores the value and writes bytes encoded earlier. The engine encodes a
    call's body from the schema first, then hands `&()` plus `Preencoded` to
    the framing (`src/engine.rs`, around line 506). This is exactly the
    pattern a C ABI needs, because codecs live in generated code.
  - **It vendors JSON-RPC** (`src/framing.rs`): "the same code the runtime
    ships, but the runtime keeps it behind `std` (module organisation, not a
    real `std` need)". That is a copy, which is the drift this proposal is
    against.
  - **It carries names separately.** Its `WireFraming` takes
    `(call_id, name)` because the name "comes from a runtime-parsed
    `ProtocolShape` (not a `&'static str` the way `contract::Call` wants
    it)".
- It keeps its own request ids instead of using `State`, so `State` has not
  been bound outside Rust yet.

## What the core owns

The rule: **the core owns everything that is bytes and integers, and nothing
that is a host value.**

1. **The handshake.**
   - Encode, decode and check of the 31-byte `comline@1` frame.
   - `name_hash`.
   - A sans-IO form of the exchange: "write our frame", then "check the
     peer's frame". The binding moves the bytes.
2. **Envelopes:** the tag byte, the `Err` ordinal, and `Fault`.
3. **All framings:** `datagram@1`, `datagram@2`, `jsonrpc@1`, and later
   versions as they are written.
   - Request and reply encode go **around a body encoded elsewhere** (the
     `Preencoded` shape, made a first-class entry point).
   - Decode returns the body as a span of the input.
4. **The connection state machine** (`State`):
   - request ids, in both directions;
   - the waiting stack, or the unordered set for an async host;
   - frame → `Request` / `Reply` / `Stale`, including the "a reply that skips
     the innermost waiting call is a framing error" rule;
   - `abandon` on timeout. The host's clock decides *when*; the core decides
     what a late reply means.
5. **Byte-level limits.**
   - The stream length prefix (`u32` LE) and `MAX_FRAME`, declared once.
   - The varint rules: shortest form only, and fits in `u16`.
   - JSON-RPC id range.
   Today these are per transport and per language. In the core they are one
   constant each.

## What it doesn't own

- **Codecs.** Encoding a value of a generated type is generated native code
  in each language, from one layout plan. See
  [stage 3](generated-codecs.md). A schema-driven codec in the core is
  rejected below.
- **Transports.** Sockets, WebSockets, pipes and stdio stay in the host. The
  core sees frames, or a stream buffer the host filled.
- **Async.** No futures, callbacks, threads or timers cross the boundary. A
  host drives the state machine from its own loop: asyncio, goroutines,
  `CompletableFuture`, `Task`, promises.
- **Generated types, dispatch tables and handlers.** These are generated per
  language. The core sees a protocol number, a call id or name, and body
  bytes.
- **Per-connection state** (`Extensions`) and interceptors. These are host
  objects.

## The C ABI

### Crate layout

```
runtime/                         ComlineProject/runtime
├── runtime/core/                comline-runtime: the reference, unchanged in role
└── runtime/ffi/                 comline-runtime-ffi (new)
    ├── Cargo.toml               crate-type = ["cdylib", "staticlib", "rlib"]
    ├── cbindgen.toml
    ├── include/comline.h        generated by cbindgen, checked in
    ├── src/lib.rs               the extern "C" surface: handles, spans, codes
    └── js/                      ES module glue for the wasm32 build, plus .d.ts
```

- **One crate, two outputs.** On native targets it builds a `cdylib` (for
  `dlopen`-style hosts: Python, Java, C#, Ruby, Dart, PHP, LuaJIT) and a
  `staticlib` (for hosts that link at build time: Go with cgo, Swift, Zig,
  C/C++). On `wasm32-unknown-unknown` the same `extern "C"` functions become
  the module's exports.
- **No `wasm-bindgen` on this surface.** The API is integers and pointers,
  which WASM exports carry as they are. Without a JS-specific layer, the
  `.wasm` *is* the C ABI. A non-JS WASM host (wazero in Go, wasmtime) then
  calls the same functions with the same semantics. The simulator uses
  `wasm-bindgen` because its surface is JS objects; this one isn't.
- **It depends on `comline-runtime` without `std`** (`default-features =
  false, features = ["alloc"]`, plus a `jsonrpc` feature once that moves; see
  [What changes in the core](#what-changes-in-the-core)). So `package_abi`
  never enters the build, and wasm32 works before stage 5. The FFI crate
  itself uses `std` for `catch_unwind`, and wasm32 has `std`.
- **The header is generated, then checked in.**
  - cbindgen is pinned, and CI fails when `include/comline.h` differs from a
    fresh run, as the docs' `cli` and `idl` drift jobs do.
  - Reviewers then see every ABI change as a header diff.
- **Why in `runtime` and not its own repo:** the FFI layer is a thin
  translation of `comline-runtime`. Splitting it would put every core change
  through a two-repo cascade. The core's tests, vectors and fuzz targets
  already live there.

### API sketch

```c
/* comline.h (sketch). All integers are fixed width; no struct is
   passed by value across the boundary except the small ones shown. */

#define COMLINE_ABI_MAJOR 0   /* 1 once frozen; see Rollout, step 5 */
#define COMLINE_ABI_MINOR 1

uint32_t comline_abi_version(void);        /* (major << 16) | minor */

typedef enum comline_status {               /* append-only, stable values */
    COMLINE_OK = 0,
    COMLINE_NEED_MORE = 1,         /* stream mode: no whole frame yet */
    COMLINE_BUFFER_TOO_SMALL = 2,  /* *written holds the size needed */
    COMLINE_ERR_FRAMING = 16,      /* RuntimeError::Framing */
    COMLINE_ERR_HANDSHAKE = 17,    /* RuntimeError::Handshake */
    COMLINE_ERR_FRAME_TOO_LARGE = 18,
    COMLINE_ERR_UNKNOWN_FRAMING = 19,
    COMLINE_ERR_INVALID_ARGUMENT = 20, /* null pointer, bad name bytes */
    COMLINE_ERR_STATE = 21,        /* e.g. a call before the handshake */
    COMLINE_ERR_POISONED = 22,     /* an earlier call panicked; drop the handle */
} comline_status;

typedef struct comline_connection comline_connection;  /* opaque */

typedef struct comline_span { uint32_t offset; uint32_t len; } comline_span;
                               /* into the caller's input buffer */

typedef enum comline_event_kind {
    COMLINE_EVENT_HANDSHAKE_OK = 0,
    COMLINE_EVENT_REQUEST = 1,
    COMLINE_EVENT_REPLY = 2,
    COMLINE_EVENT_STALE = 3,
} comline_event_kind;

typedef enum comline_envelope_kind {
    COMLINE_ENVELOPE_OK = 0, COMLINE_ENVELOPE_ERR = 1, COMLINE_ENVELOPE_FAULT = 2,
} comline_envelope_kind;

typedef struct comline_event {
    uint8_t      kind;          /* comline_event_kind */
    uint8_t      flags;         /* HAS_PROTOCOL, ONE_WAY, CALL_BY_NAME, BODY_ABSENT */
    uint16_t     protocol;      /* valid with HAS_PROTOCOL */
    uint16_t     call_id;       /* valid without CALL_BY_NAME */
    uint8_t      envelope;      /* comline_envelope_kind, for REPLY */
    uint8_t      _reserved;
    uint16_t     error_id;      /* the schema-global ordinal, for ENVELOPE_ERR */
    uint64_t     request_id;
    comline_span call_name;     /* valid with CALL_BY_NAME (jsonrpc@1) */
    comline_span body;          /* params for REQUEST, payload or error body for REPLY */
    comline_span frame;         /* the whole frame, for logging or forwarding */
} comline_event;

typedef struct comline_config {
    uint64_t    ir_hash;
    const char* wire_format;  size_t wire_format_len;   /* "packed@1" */
    const char* framing;      size_t framing_len;       /* "datagram@2" */
    uint32_t    capabilities;
    uint8_t     handshake;    /* COMLINE_HANDSHAKE_COMLINE or _NONE */
    uint8_t     stream;       /* 1: u32 LE length-prefixed byte stream; 0: one frame per message */
    uint8_t     unordered;    /* 1: replies in any order (async hosts) */
    uint16_t    max_waiting;  /* waiting-call capacity, fixed at create */
    uint32_t    max_frame;    /* <= COMLINE_MAX_FRAME (16 MiB); 0 = the default */
} comline_config;

comline_status comline_connection_new(const comline_config* cfg, comline_connection** out);
void           comline_connection_free(comline_connection* conn);
```

The three representative calls:

```c
/* 1. Feed bytes, get the next event. One frame per call.
 *
 * Stream mode: `in` is whatever the host has read so far. If a whole
 * length-prefixed frame is there, it is decoded, *consumed is set to the
 * prefix + frame length, and *ev describes it, with spans relative to `in`.
 * Otherwise COMLINE_NEED_MORE, *consumed = 0, and ev->frame.len holds the
 * total bytes needed once the prefix itself is complete (0 before that).
 *
 * Message mode: `in` is exactly one frame.
 *
 * The first frame on a COMLINE_HANDSHAKE_COMLINE connection is the peer's
 * handshake: it is checked and yields HANDSHAKE_OK or COMLINE_ERR_HANDSHAKE. */
comline_status comline_connection_feed(
    comline_connection* conn,
    const uint8_t* in, size_t in_len,
    size_t* consumed,
    comline_event* ev);

/* 2. Frame a request around a body the generated codec already wrote.
 *
 * `name` is used by name-oriented framings (jsonrpc@1) and ignored by the
 * datagram framings. It must be an identifier (no JSON escaping), or the
 * call fails with COMLINE_ERR_INVALID_ARGUMENT. In stream mode the length
 * prefix is written too, so `out` is ready for one transport write.
 *
 * On COMLINE_BUFFER_TOO_SMALL, *written is the size needed and the
 * connection is unchanged: no request id is spent and nothing is waited on. */
comline_status comline_connection_encode_request(
    comline_connection* conn,
    uint16_t protocol, uint16_t call_id,
    const uint8_t* name, size_t name_len,
    uint8_t expects_reply,
    const uint8_t* body, size_t body_len,
    uint8_t* out, size_t cap, size_t* written,
    uint64_t* request_id);

/* 3. Frame the reply to a request this side was given. */
comline_status comline_connection_encode_reply(
    comline_connection* conn,
    uint16_t protocol, uint64_t request_id,
    uint8_t envelope, uint16_t error_id,
    const uint8_t* body, size_t body_len,
    uint8_t* out, size_t cap, size_t* written);
```

The rest of the surface is small:

- `comline_connection_start(conn, out, cap, written)` writes this side's
  handshake frame.
- `comline_connection_abandon(conn, request_id)` gives up on a call after a
  timeout.
- `comline_connection_is_waiting(conn)`.
- Free functions with no handle: `comline_name_hash`,
  `comline_handshake_encode` and `comline_handshake_check`, for hosts that
  run the handshake themselves.

A call from Python, Go or Java is then:

```
generated codec:  value -> body bytes          (native, stage 3)
core:             body -> frame                (1 crossing)
host:             write(frame)                 (native I/O, native async)
host:             read() -> buffer
core:             buffer -> event + spans      (1 crossing)
generated codec:  buffer[span] -> value        (native, stage 3)
```

In Rust, `comline-runtime` keeps calling `State` and the framings directly.
The FFI layer is for every other language, and Rust never pays for it.

### Rules

**One crossing per frame, never per field.**
- Each of `feed`, `encode_request` and `encode_reply` handles one whole
  frame.
- Nothing calls back into the host: no callbacks, no host allocator, no
  per-field accessor.
- An event is a plain struct the host reads with its own field loads.

**No allocation crosses the boundary.**
- Every output buffer is the caller's (`out`, `cap`, `*written`).
- Every input is borrowed for the duration of the call only.
- The one thing the library allocates is the handle. It does so once, in
  `comline_connection_new`, sized by `max_waiting`, and frees it in
  `comline_connection_free`. The host never frees library memory and the
  library never frees host memory.
- After the handle exists, the happy path allocates nothing. That needs
  `State.waiting` to become a fixed-capacity array and `jsonrpc@1` to stop
  formatting ids through `String`. Both are listed under
  [What changes in the core](#what-changes-in-the-core), and both already
  apply to Rust callers under
  [§4.6's budget](../../design/core-target-contract.md#the-budget)
  ("**zero** allocations on the happy path").
- A host with no allocator story of its own (embedded C, Zig) can get a
  later `comline_connection_size(cfg)` / `comline_connection_init(mem, …)`
  pair. That is a minor ABI addition, not part of 1.0.

**Panics never cross.**
- Since Rust 1.81, a panic unwinding out of an `extern "C"` function aborts
  the process. That is never undefined behaviour, but aborting a Python
  interpreter or a JVM is not acceptable either.
- **Policy:** the release profile keeps `panic = "unwind"`. Every exported
  function body runs inside `catch_unwind`, which costs nothing when there is
  no panic.
  - A caught panic marks the handle poisoned and returns
    `COMLINE_ERR_POISONED`.
  - Every later call on that handle returns the same code, so the binding
    closes the connection.
- **On wasm32,** a panic is a trap (`WebAssembly.RuntimeError`). The JS glue
  catches it and discards the instance. Unwinding on wasm32 needs the
  exception-handling proposal, which this does not depend on.
- **Panics are bugs, not a control path.** The decode paths are already
  written as `Option`-returning `split_at_checked` chains. Stage 1's fuzz
  targets run against the FFI entry points with "no panic" as the check.

**Thread safety.**
- A `comline_connection*` is **movable, not shareable**. Any thread may use
  it, but calls on one handle must not overlap. The binding enforces this
  however its host does: a mutex in Go, confinement or a lock in Java and C#,
  a lock per handle in Python (the GIL alone is not enough on free-threaded
  builds).
- Different handles are independent. The FFI layer keeps no global mutable
  state. `next_connection_id`'s static atomic lives in the blocking driver,
  which the FFI doesn't use.
- The free functions are pure and re-entrant.

**ABI versioning.**
- **The ABI has its own version,** separate from the crate version
  (`comline-runtime` is `0.1.0`) and from encoding versions (`datagram@2`).
  - The major changes when any existing signature, struct layout or code
    meaning changes.
  - The minor changes when functions, codes or flag bits are added.
- **The header carries `COMLINE_ABI_MAJOR` / `_MINOR`.**
  `comline_abi_version()` returns the library's.
- **At load, before any other call, a binding refuses a library**
  - whose major differs from its header's, or
  - whose minor is lower than its header's.
  It refuses with an error naming both versions. It never refuses lazily on
  first use.
- **Before 1.0, a minor counts as a major.** A binding built against `0.n`
  accepts only `0.n`, so nothing pre-release is mistaken for compatible.
- **Structs are frozen within a major.** New data comes through new
  functions or new flag bits. A `struct_size` field is not used, because
  every binding would have to honour it.
- **Status codes and flag bits are append-only.** A binding maps an unknown
  status to a generic error carrying the number. `RuntimeError` is already
  `#[non_exhaustive]`, for the same reason.
- `comline_supports(name, len)` answers whether this library build knows an
  encoding name (`"datagram@2"`). A binding can then refuse a schema's
  `@framing` at setup, not at the first frame.

**Zero-copy where the host allows.**
- **Input is borrowed.** Events point into it by `comline_span` offsets, so
  the core never copies a body out.
  - The datagram framings already return params and envelopes as subslices
    of the frame.
  - `jsonrpc@1` already borrows `params`, `result`, `error.data` and
    `method` through `RawValue` and `&str`.
- **Offsets, not pointers.** A span stays valid if the host moves or
  reallocates its buffer between the call and the decode. A garbage-collected
  host (Java heap arrays, .NET with pinning only during the call, Go)
  usually does exactly that.
- **`u32` spans are enough:** `MAX_FRAME` is 16 MiB. They are also the same
  width on wasm32.
- **Two JSON-RPC edge cases surface as flags, not copies:**
  - Absent `params` or `result` decode today as the literal `null` (a static
    slice, not part of the input). The event sets `BODY_ABSENT` with an empty
    span, and the JSON codec reads `null`.
  - `serde_json` will not borrow a string that contains escapes, so a
    `method` with a `\u` escape fails to decode today. The FFI keeps that
    behaviour. A vector should pin it before anything changes it.
- **Output is written once,** straight into the caller's `out`. The body
  passed to `encode_*` is copied exactly once, into the frame. That is the
  same single copy the Rust path makes when `Packed` encodes into the send
  buffer.

### What changes in the core

All of these are small. Each one also helps Rust callers.

| Change | Why |
|---|---|
| Body-bytes entry points on `Framing` / `ConnectionFraming` (`encode_request_body(…, body: &[u8], …)`), the generic `Serialize` form becoming a wrapper | The `Preencoded` shim, made first-class. The simulator can drop its copy. |
| `Call::name` borrowed (`&'a str`) rather than `&'static str` | Host-owned names; the simulator's `WireFraming` workaround goes away. |
| `jsonrpc@1` behind `alloc` or its own `jsonrpc` feature, not `std`; ids written without `to_string` | The simulator vendors it today. Whether `serde_json`'s `raw_value` builds without `std` has to be checked first. |
| `State.waiting` with a capacity fixed at construction | No allocation on the happy path; an overflow becomes an error code, not a reallocation. |
| A sans-IO stream deframer: the `u32` LE prefix plus one `MAX_FRAME` constant | Replaces the two declarations in `transport.rs` and the tokio `Tcp`. |
| A sans-IO handshake step (`ours.encode`, `check(peer_bytes)`) beside `ComlineHandshake` | `ComlineHandshake::exchange` is `Transport`-bound. |
| A counting `BufMut` | So `BUFFER_TOO_SMALL` can report the exact size needed without mutating state. |

## WASM

**The same API, compiled to `wasm32-unknown-unknown`.**
- `comline-runtime-ffi` exports the `comline_*` functions as they are.
- `js/` holds a small ES module, hand-written, with no generated glue. It
  - instantiates the module;
  - reserves an input region and an output region in linear memory, through
    two wasm-only exports (`comline_wasm_reserve_in(len)`,
    `comline_wasm_reserve_out(len)`) that return pointers into memory the
    module owns;
  - reads `comline_event` with a `DataView`.
- **A size reference point:** the simulator's 2026-09-03 spike, built on
  `comline-runtime` with `alloc` only, was an 88 KB `.wasm`.

**The copy is the honest cost.**

| Step | Cost |
|---|---|
| Bytes from the socket (a `Uint8Array` on the JS heap) into linear memory | one `set()`, a memcpy linear in frame size, per frame in |
| The call | a JS→WASM call; small in current engines, not free |
| Spans back | read through `DataView`; no copy |
| The body, for the generated JS codec | read in place through a view on `memory.buffer`, **or** copied out if the codec keeps it past the next call |
| A frame out | the codec's body is copied in, the frame is copied out: two memcpys |

- **Views on `memory.buffer` are invalidated when memory grows.** The glue
  reserves its regions up front and only grows between calls. Even so, a
  generated codec must not hold a view across calls.
- **For small frames this can lose** to hand-written TypeScript framing,
  which works on the socket's `Uint8Array` with no copy. A `datagram@2`
  request header is 12 bytes for a protocol number below 128; the copy and
  the call are fixed costs around very little work.
- That is why [stage 4](index.md#stages) moves TypeScript piece by piece,
  and only where the [stage 1 gates](verification.md) show the core is at
  least as fast for that host. The browser has no native option, so there
  the comparison is WASM against pure TypeScript only.

**The component model and WIT: a later option, not the plan.** The WASM
component model would let a WIT interface generate bindings for many host
languages. As of this writing:

- **Mature enough to rely on:**
  - WASI 0.2 (Preview 2, January 2024) and the component model in wasmtime,
    on the Rust host side;
  - `wit-bindgen` for Rust guests;
  - `jco` for running components in Node and, after transpiling, in
    browsers.
- **Not mature enough to rely on:**
  - Host-side component support outside Rust and JS is uneven: Python, Go,
    Java, .NET, Ruby and PHP each depend on a third-party engine binding, at
    varying stages.
  - Async in the component model is WASI 0.3 work, still in progress.
  - Browsers have no native component support; it goes through `jco`.
  - The canonical ABI copies values between instances. That is the cost this
    page avoids with spans.

So a WIT surface would not cover the languages Comline targets today without
also keeping the C ABI. **Re-assess after stage 2 ships.** If the WIT
toolchain has caught up by then, a WIT world mirroring `comline.h` is an
addition, not a replacement.

**The `package_abi` leftover.**
- `runtime/core/src/package_abi` pulls `abi_stable` and `libloading` under
  `std`, which is why `comline-runtime` with `std` doesn't build for wasm32.
- The FFI crate avoids it by not enabling `std`, but the trap stays for
  anyone else.
- Stage 5 removes it, or splits it into its own crate. It belongs to `dylib`
  mode, which is a different idea from this core.

## Per-language bindings

**The rule:**
- Every language binds the core, natively or through WASM.
- **A pure implementation is allowed only where both native and WASM lose to
  it by measurement**, against the [stage 1 gates](verification.md).
- A pure implementation is held to everything the core is held to:
  - the byte-exact vectors;
  - differential fuzzing against the Rust core, with the same malformed
    inputs refused;
  - the benchmark gates.
- It is an exception that each language's CI has to keep earning, not a
  default.

| Language | Mechanism | Ships as | Known costs and caveats |
|---|---|---|---|
| C, C++ | `comline.h` directly | static or shared lib + header | None beyond the ABI rules; C++ can add an RAII wrapper. |
| Zig | `@cImport("comline.h")`, static link | static lib + header, or a `build.zig` dependency | None notable. |
| Rust | `comline-runtime` directly, no FFI | crate | The reference; never goes through the C ABI. |
| Python | `cffi` (API mode, compiled) over the C ABI; `pyo3` only if gates show it wins | wheels per platform, via `maturin` or `cibuildwheel` | `ctypes` is rejected: per-call overhead is far higher. `pyo3` would bind the Rust API, not the C ABI, so it would be a second surface and has to earn that by measurement. Free-threaded builds need the per-handle lock. |
| Go | cgo, static link | module with vendored `.a` per `GOOS/GOARCH`, or a build step | Each cgo call has a fixed overhead (tens of nanoseconds), so one crossing per frame matters most here. cgo needs a C toolchain and complicates cross-compiling. **Without cgo** (`CGO_ENABLED=0`, which many Go shops require): the same `.wasm` in wazero (a pure-Go runtime), or a pure Go implementation under the rule above. Measurement picks. |
| Java | Panama FFM (`java.lang.foreign`, final in Java 22), header via `jextract` | jar with native libs per platform | JDK 21 and older need JNI or JNA. Android has no FFM; it uses JNI. Heap arrays need copying to a `MemorySegment`, or the host reads into off-heap segments from the start. |
| Kotlin | JVM: as Java. Android: JNI. Native: `cinterop` | as Java; `.aar` for Android | Three mechanisms for one language; the JVM one comes first. |
| C# / .NET | P/Invoke, `[LibraryImport]` source-generated marshalling | NuGet with `runtimes/<rid>/native/` | Blittable structs and spans keep marshalling at zero; `Span<byte>` pins only for the call. |
| Swift | the C header through a module map | SwiftPM `binaryTarget` (XCFramework) on Apple; static lib on Linux | XCFramework covers device and simulator slices. |
| Ruby | `ffi` gem; a native extension if gates require | platform gems | `ffi` goes through libffi; per-call cost is higher than a compiled extension. |
| Dart / Flutter | `dart:ffi`, header via `ffigen` | package with native libs; Dart's build hooks ("native assets") where available | Check the build-hooks status when implementing; Flutter mobile needs the Android and iOS triples. |
| PHP | `FFI` extension (PHP 7.4+) | `.so`/`.dll` + header in the package | `ffi.enable` defaults to `preload`, so FFI is off outside the CLI unless preloaded. Per-call FFI overhead is high; a pure implementation may win here, and the gates decide. |
| Lua | LuaJIT: `ffi.cdef`. PUC Lua: a small C module over the ABI | LuaRocks rock | LuaJIT's FFI is fast; PUC Lua needs the C module. Luau has no FFI, so the embedder exposes it. |
| Node, Bun, Deno | napi over the C ABI (static link into a `.node` addon); WASM as a fallback | npm, one package per platform under `optionalDependencies` | napi calls are cheap, but the stage 4 small-frame question applies. Bun and Deno load napi addons to differing degrees; WASM works everywhere. |
| Browser | WASM only | npm, or the `.wasm` + `js/` glue | The linear-memory copy, stated above. Pure TypeScript is the alternative, and the gates decide. |

## Distribution

**This is a sketch and an open question.** It needs its own pass before
stage 2 ships.

**Targets.** Prebuilt binaries per triple, from `runtime`'s release
workflow:

- `x86_64-unknown-linux-gnu`, `aarch64-unknown-linux-gnu`, and their `-musl`
  twins;
- `x86_64-apple-darwin`, `aarch64-apple-darwin`;
- `x86_64-pc-windows-msvc`, `aarch64-pc-windows-msvc`;
- `aarch64-linux-android`, `armv7-linux-androideabi`;
- `aarch64-apple-ios`, `aarch64-apple-ios-sim`;
- `wasm32-unknown-unknown`.

**How each ecosystem ships them:**

| Ecosystem | Pattern |
|---|---|
| Python | wheels tagged per platform (`manylinux`, `musllinux`, macOS, Windows) |
| npm | one package per platform, selected by `os`/`cpu` under `optionalDependencies`, plus a WASM fallback package |
| Maven | one jar per platform classifier, or one jar holding every platform's library, extracted at load |
| NuGet | `runtimes/<rid>/native/` in one package |
| Go | static libs per `GOOS/GOARCH` committed to the module with `#cgo LDFLAGS` per platform. A build step that needs `cargo` is the alternative, and a worse experience. |
| SwiftPM | `binaryTarget` with a checksummed XCFramework |
| Ruby | platform gems |
| Dart, PHP, Lua | native libs inside the package; specifics per ecosystem |

**Reproducibility.**
- Release builds use a **pinned stable toolchain**. The runtime repo's
  `rust-toolchain` currently says `nightly`, unpinned, and that can't stay
  for shipped binaries.
- Builds run with `--locked`, `--remap-path-prefix` and a fixed
  `SOURCE_DATE_EPOCH`, and the release publishes checksums.
- Each binding records the core release it bundles in a file, as
  `VECTORS_REV` does for conformance today. A language bumps it on purpose.

**Open:**
- whether binaries are released from `runtime` once and pulled by each
  language's packaging, or built in each `comline-<lang>` repo from a pinned
  rev;
- signing;
- the Go repository size if every platform's `.a` is committed;
- how bumping the bundled core rev is ordered across repos, as
  `comline-core` and `STD_REV` bumps already are.

## How it fits one repository per language

The [2026-08-31 decision](../../design/runtime-repo-structure.md) still
holds:

- **`runtime`** holds the core, `comline-runtime-ffi`, `comline.h`, the
  conformance vectors and the fuzz targets, and releases the prebuilt
  libraries.
- **Each `comline-<lang>`** holds:
  - that language's **thin binding** (load, version check, spans to host
    slices, the per-handle lock);
  - its **generator backend**;
  - its CI with the stage 1 gates.
  The binding and the generated code it serves still change together in one
  CI.
- **`comline-typescript`'s `runtime/`** shrinks toward a binding as stage 4
  moves pieces, where the gates allow.
- **`comline-rust`** is unaffected; Rust uses the crate.

This answers the open seam in
[`core-target-contract.md` §4.7](../../design/core-target-contract.md#47-still-open-beyond-the-above),
"the per-language-runtime ↔ core-runtime seam". It does **not** answer §5:
that is `dylib` mode, a generated package as a loadable object, and it
stays a separate idea.

## Alternatives rejected under the constraint

| Alternative | Why it's rejected |
|---|---|
| **WASM everywhere.** One `.wasm`, every host embeds an engine. | **Performance:** outside JS, a WASM call through an embedded engine (wasmtime, wazero) costs more than a native call, and every frame is copied into linear memory and out. **Distribution:** every host ships an engine, itself a native dependency, so nothing is saved. WASM stays for the hosts that need it: browsers, and Go without cgo if it measures better there. |
| **Per-language reimplementation.** The status quo. | **Correctness and conformance:** the copies drift. Five interop bugs in TypeScript were found the day the corpus landed, and comline-typescript#57 is open. Every wire feature this month was built twice. At ten languages that is ten copies of every fix. Kept only as the measured exception above. |
| **A schema-driven codec in the core.** Hosts hand values to the core, which encodes them from the schema, as the simulator's `packed.rs` does over `serde_json::Value`. | **Performance:** every call converts host values into a core representation, field by field, across the boundary. That is many crossings per call, or a second serialization to get one. It is slower than native generated code in every language. Codecs are [stage 3](generated-codecs.md), generated per type. The simulator does this because it is schema-driven by nature, not for speed. |
| **`abi_stable`** (as `package_abi` used). | It is a Rust-to-Rust stable ABI: its types (`RVec`, prefix types) are for Rust on both sides. A C, Go or Java consumer can't use them, and the C ABI is what those consumers need. This is how the 2023–24 attempt stalled. |
| **`wasm-bindgen` as the WASM surface.** | It produces a JS-only surface. The `.wasm` would then not be the C ABI, and Go-without-cgo through wazero would need a second surface. |
| **One crossing per field or per event poll** (a `feed`, then `poll` until empty). | Two or more crossings per frame where one does. On cgo, PHP and Ruby `ffi` the fixed per-call cost dominates small frames. `feed` returns the frame's event directly; a stream buffer holding several frames is fed again from `consumed`. |

## Open questions

- **Handle memory for no-allocator hosts:** whether
  `comline_connection_size` / `comline_connection_init` belongs in 1.0 or
  1.1.
- **`max_waiting` overflow:** whether it is an error to the caller of
  `encode_request`, as proposed, or the binding's job to queue.
- **`pyo3` vs `cffi` for Python,** and whether a second binding surface is
  ever worth it. Decided by gates, but the default needs picking.
- **Go without cgo:** wazero against pure Go, measured on the same
  benchmarks.
- **Whether `jsonrpc@1`'s `serde_json` dependency** fits the no-`std` FFI
  build as is, or needs a narrower parser for the envelope fields.
- **Distribution:** everything flagged in [Distribution](#distribution).
- **Whether `comline@2`'s negotiation** (protocol numbers handed out at the
  handshake) changes the event struct. If so, it should land before ABI 1.0
  freezes.

## Rollout

1. **The core changes** in `comline-runtime`, each with vectors: body-bytes
   framing entry points, borrowed `Call::name`, `jsonrpc@1` out of `std`,
   fixed-capacity `waiting`, the stream deframer with one `MAX_FRAME`, and
   the sans-IO handshake step. The simulator moves onto them and deletes its
   vendored JSON-RPC and `Preencoded`.
2. **`comline-runtime-ffi`** with `comline.h` at ABI `0.x`: native and wasm32
   builds, the header drift check, and FFI fuzz targets in stage 1's
   harness.
3. **A C test binding** in `runtime` CI runs the conformance vectors through
   the C ABI and the wasm32 build. This proves the boundary before any
   language depends on it.
4. **The first two real bindings, chosen to stress the boundary:**
   - **TypeScript**, through WASM and napi: stage 4's question;
   - **Go**, through cgo: the most expensive call.
   Both run the stage 1 gates against the TypeScript runtime and a pure-Go
   baseline.
5. **ABI 1.0** once both bindings pass, then the release workflow and
   prebuilt binaries.
6. **Further languages** each bring a binding and a generator backend in
   their own repo.

## What it touches

- **Runtime:**
  - the `comline-runtime` changes above;
  - the new `runtime/ffi` crate, header and JS glue;
  - FFI fuzz targets;
  - the release workflow;
  - the workspace `Cargo.toml`, where the `runtime-langs/c` stub (an `add`
    function today) is superseded.
- **Simulator:** drops its vendored JSON-RPC and the `Preencoded` shim once
  the core has body-bytes entry points.
- **comline-typescript:** stage 4, behind the gates.
- **Each future `comline-<lang>`:** a binding, its packaging, and the gates.
- **Docs:**
  - the [runtime guide](../../guide/runtime/index.md)'s "no FFI boundary";
  - [`core-target-contract.md`](../../design/core-target-contract.md) §4.7
    (answered here) and §4.6's `no_std` layering table;
  - a `comline.h` reference page.
