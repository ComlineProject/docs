# IPC

Status: **draft** · Handles are typed, one type per kind (decided
2026-11-02) · Builds on [Transports](transports.md) and
[Connections](connections.md) · Handles answer part of the open
[capabilities design](https://github.com/ComlineProject/docs/issues/98) · The
first step of [Comline for systems software](systems-software.md) ·
[Framings](#framings) laid out against
[Dependency protocols, Part 1](dependency-protocols/capabilities.md)

**The question:** what does Comline need to be a good interface between
processes on one machine, beyond what a network connection needs?

Where things stand:

- **The runtime calls itself an RPC/IPC runtime,** but nothing designs IPC.
  The [runtime contract](../design/core-target-contract.md) lists Unix sockets
  and in-process among transports and stops there.
- **What already suits IPC:** the Rust runtime's lowest tier is `no_std` with
  no allocator; dispatch is synchronous; decoders refuse hostile lengths before
  allocating; generated code forbids `unsafe`; the shared runtime core has a C
  ABI.
- **[Connections](connections.md)** plan peer information from the transport
  in each connection's state, and interceptors that can reject calls (for
  authorization) before they reach a handler.
- **[Transports](transports.md)** is a draft: optional declarations, transport
  profiles with stated facts, and a "transport fit" guarantee where declared.

## What makes IPC different

| Topic | Over a network | Between processes |
|---|---|---|
| Transports | TCP, UDP, WebSocket | Unix sockets, pipes, shared memory, and each platform's own IPC |
| What can be sent | bytes | bytes, **and handles**: file descriptors, shared memory, endpoints to call |
| Large payloads | copied | can be shared in place, through shared memory |
| Who the peer is | what the peer proves (TLS) | **what the OS reports:** its process, user, sandbox |
| A peer that dies | noticed by a timeout | **reported by the OS** at once |
| Versions | independent deployments | often shipped together, but partial updates still mix versions |
| Latency | milliseconds | microseconds: per-call overhead dominates |

## IPC transports

Profiles in the [transports](transports.md#transport-profiles) shape, with three
facts IPC adds:

- **`handles`:** which kinds of handle the transport can carry, and how many
  per message (Linux allows 253 file descriptors per message; a Zircon channel,
  64);
- **`peer_identity`:** what the OS reports about the peer;
- **`peer_death`:** whether the OS reports a peer's exit.

| Profile | Boundaries | Handles | Peer identity | Peer death |
|---|---|---|---|---|
| `unix-stream@1` | a stream | file descriptors | process, user, group | on close |
| `unix-seqpacket@1` | messages | file descriptors | process, user, group | on close |
| `pipe@1` (anonymous pipes, stdio) | a stream | none | the parent knows its child | on close |
| `windows-pipe@1` | messages or a stream | handles, duplicated by the sender | the client's process and token | on close |
| `memory-ring@1` (a shared-memory ring, Comline's own, later) | messages | none in the ring | from the handle that set it up | needs a side channel |
| Platform IPC, each its own profile: Mach and XPC (macOS), Binder (Android), D-Bus (Linux), ALPC (Windows), Zircon channels (Fuchsia) | messages | each platform's own | each platform's own | each platform's own |
| `postmessage@1` (browsers, workers, Electron) | messages | transferable objects (`MessagePort`, `ArrayBuffer`) | the origin | page or worker lifetime |

## Handles

A handle is something the OS lets one process give another: an open file, a
shared memory region, an endpoint of another channel. It travels **beside** the
bytes, not in them.

### The options

| | In the schema | In one line | Assessment |
|---|---|---|---|
| **H1** | `handle` | one opaque type for any handle | rejected: a receiver can't tell a file from a memory region, so it can't check what it was given |
| **H2** | `file`, `memory`, `channel`, and endpoints of a protocol | **a type per kind of handle**, each checked on arrival | **decided** 2026-11-02 |
| **H3** | nothing: handles are a transport feature, passed beside calls | handles outside the schema | rejected: the schema couldn't say which call carries which handle, so nothing could check it |

### H2: a type per kind

| Type | What it is | Rust | C |
|---|---|---|---|
| `file` | an open file, socket or pipe | `OwnedFd` / `OwnedHandle` | `int` / `HANDLE` |
| `memory` | a shared memory region; `memory[max N]` bounds its size in bytes | a mapped-region type | a descriptor and a size |
| `channel` | a raw IPC endpoint | the transport's endpoint | its handle |
| `remote Orders` | an endpoint to **call** protocol `Orders` | a client for `Orders` | a client handle |
| `receiver Orders` | an endpoint to **serve** `Orders` | a server binding for `Orders` | a server handle |

`remote` and `receiver` are capabilities in the Cap'n Proto and Mojo sense: a
call can hand the peer a new, typed connection. That's the capabilities part of
the open design.

```ids
protocol Files {
    /// Opens a file and hands it to the caller.
    function open(path: char[max 4096]) -> file;
    /// Shares a frame buffer without copying it.
    function frame() -> memory[max 8388608];
    /// Gives the caller its own session, served on a new channel.
    function session() -> remote Session;
}
```

**How they work, whichever spelling is chosen:**

- **On the wire,** a handle is encoded as its index in the message's
  attachments: a `u32` in `packed@1`, a number in `json@1`. The handles
  themselves go through the transport.
- **Checked on arrival:** the decoder checks each handle is the kind the schema
  says (`fstat`, `zx_object_get_info` and their equivalents), and that the
  message carries exactly the handles its body refers to. An unexpected or
  wrong handle is refused, and closed.
- **Ownership moves:** sending a handle gives it away; the sender keeps a copy
  only by duplicating it first. A received handle is owned by the receiver.
  Every handle in a refused message is closed, so nothing leaks.
- **Bounded like everything else:** an array of handles needs a maximum, and
  the transport's own limit per message is part of transport fit.
- **Transport fit becomes required, not optional:** a protocol that sends a
  handle can only run over a transport that carries that kind. That's checked
  at build, against the transports declared ([Transports](transports.md)), and
  a protocol using handles must declare one.
- **Version comparison:** changing a handle's kind is breaking.
- **Languages:** Rust and C map to the OS types. TypeScript has handles only in
  Node (file descriptors over Unix sockets, in limited cases) and in browsers
  (transferables over `postMessage`); its support claim says which.

### Rights

A right restricts what the receiver can do with a handle: read but not write,
map but not execute. It matters most for handing a sandboxed process a
**read-only** view of a buffer or a file. Some systems attach rights to every
handle (Zircon: read, write, map, duplicate; Mach: send and receive rights).

Open, to be settled after the rest of IPC:

| | Option | Trade-off |
|---|---|---|
| **R1** | no rights in the schema: the kind only | simplest; the receiver can do whatever the OS lets the handle do |
| **R2** | a small portable set in the schema (`read`, `write`), as in `memory(read)` | the sender drops extra rights before sending, and the decoder verifies them. Every platform can express read and write: a file's open mode and sealed shared memory (`memfd` seals) on Linux, access masks on Windows, rights on Zircon |
| **R3** | each platform's full set of rights | the most precise, but not portable |

Adding rights later tightens existing protocols, a breaking change, so it's
best settled before 1.0. If rights come, R2 is the recommendation: read-only
sharing is the real security need, and its small set works everywhere.

## Framings

What runs inside a connection over an IPC transport. A framing is described
by the facts and limits of
[Dependency protocols, Part 1](dependency-protocols/capabilities.md). IPC
asks for things no network framing has had to state, and a framing that
can't state them doesn't belong over IPC.

There are three kinds:

- Comline's own framings, run over IPC transports.
- Framings for **channels handed over in a call** (`remote P`, `receiver P`).
- Each **platform's own** framing, for talking to its services.

### What IPC asks of a framing

| Need | Why | What it asks |
| --- | --- | --- |
| **Handles belong to one frame** | the decoder checks that a message carries exactly the handles its body refers to | something must say which handles arrived with which frame: the transport or the framing ([below](#who-ties-handles-to-a-frame)) |
| **Low per-call overhead** | calls take microseconds, so the header is a large share of the work | fixed-width headers at fixed offsets, with no varints ([`datagram@4`](dependency-protocols/datagram@4.md#why-fixed-widths)) |
| **One-way calls and events** | OS services push events and notifications | one-way calls marked in the frame, so a receiver never answers one |
| **Calls in both directions** | callbacks into the client | `directions = both` |
| **Handles in replies** | `-> file` | a reply carries handles like a request does. A fault carries none, and whatever the provider meant to send is closed |
| **Channels created by calls** | `remote P` and `receiver P` | a framing and an agreement for the new channel ([below](#channels-handed-over-in-a-call)) |
| **A peer that dies** | the OS reports it | nothing from the framing: the transport closes the connection, and every pending call fails |

### Who ties handles to a frame

| | Who | How | Trade-off |
| --- | --- | --- | --- |
| **T1** | the transport | A message transport (`unix-seqpacket@1`, Zircon and Mach channels, Windows message pipes, `postmessage@1`) delivers handles with the message. A stream transport (`unix-stream@1`) sends a frame's handles in the same `sendmsg` as the frame, and its length prefix gains a handle count, so the receiver takes exactly that many | frames are the same bytes over TCP and IPC, and the framing states nothing new. Each stream transport needs the count |
| **T2** | the framing | the frame's header states how many handles it carries, as D-Bus's `UNIX_FDS` field does | every framing that runs over IPC grows a field, or gets an IPC version of its own |

**Decided 2026-11-14: T1.** It's the model above, where handles travel beside the bytes:
the transport carries the handles, the format encodes their indices, and the
framing carries the bytes. Comline's own framings then state `handles =
by_transport`. A platform's framing that counts or lists handles states that
instead (see [Facts IPC adds](#facts-ipc-adds)).

The most handles one message can carry is the transport's limit (253 file
descriptors per message on Linux, 64 handles on a Zircon channel), unless a
framing that counts them states a lower one. The build checks each call's
largest number of handles against it, which is why an array of handles needs
a maximum.

### Comline's own framings over IPC

| framing + handshake | Over IPC | Request / reply header |
| --- | --- | --- |
| [`datagram@4`](dependency-protocols/datagram@4.md) + `comline@3` | **the default:** fixed widths, one-way marked, several packages, compatible versions connect | 9 / 7 bytes, a one-way 5 |
| `datagram@3` + `comline@2` | works, for one package. Varint numbers cost branches on every call | 11 to 15 / 10 to 12 bytes |
| `jsonrpc@1` | for scripted peers: Node, browsers over `postmessage@1`, Electron | JSON text |
| `datagram@2` + `comline@1` | works, but every peer must be rebuilt from identical schemas, which partial updates break | 12 / 10 bytes, a protocol past 127 one more |

The handshake costs one message each way, once per connection, and IPC
connections usually live as long as the process.

### Channels handed over in a call

A call returning `remote Session` hands the caller a new channel endpoint,
already typed by the schema. What runs on that channel:

- **The framing and format are the parent connection's.** They're stated once,
  by the package, not chosen per channel.
- **Every child channel starts with a handshake** (decided 2026-11-14). The
  connection's handshake, `comline@3`, runs on it before the first call, with
  a Hello of one package and one protocol. That protocol is connection number
  0.
- **Why not inherit the parent's agreement.** It's tempting: the parent's
  handshake already agreed the schema that types the endpoint, and Mojo and
  FIDL skip a handshake per pipe or channel. But endpoints can be
  **forwarded**. An endpoint created between A and B, then sent on by B to C,
  connects A and C directly, and the OS moves it, so B is out of the path. A
  and C never agreed on anything, and **A can't tell** that its channel's
  other end changed hands. Detecting forwarding would take a first frame that
  may be a Hello or a call, and calls held until the check passes. Sending the
  creator's facts along would ship data where a cheap check that can fail
  does the job. A handshake on every child channel is correct whoever holds
  the endpoint, and needs nobody to know.
- **What it costs:** one round trip per child channel before its first call,
  with a small Hello. A design that creates many short-lived channels pays it
  each time.
- **The protocol field is constant.** Under `datagram@4` a child channel's
  protocol is always 0: 2 bytes per frame spent on nothing. That's cheaper
  than a framing of its own.
- **Outliving the parent.** A child channel is its own channel, with its own
  agreement, so it stays valid after the parent connection closes.

### Platform IPC framings

Each platform's IPC has its own message layout, so each is its own framing,
often with its own format. Like a legacy packet system
([Packet dispatch](packet-dispatch/index.md#describing-legacy-protocols)), it's an
encoding a package names to talk to the platform's services, and its profile
describes it in Part 1's terms:

| Platform | Names the function | Names the protocol | Matches a reply | One-way | Handles | Errors |
| --- | --- | --- | --- | --- | --- | --- |
| **D-Bus** | by its member name | by its interface name, plus an object path | the reply's serial (`u32`) in the header | a `NO_REPLY_EXPECTED` flag | counted in the header (`UNIX_FDS`) | by error name |
| **Binder** (AIDL) | a transaction code, from declaration order unless stated | an interface token, per object | the reply comes back on the calling thread | `FLAG_ONEWAY` | objects and file descriptors in the parcel, listed by offset | in the reply parcel |
| **Mojo** | a method ordinal, from declaration order unless stated | per message pipe; an associated interface gets an id bound at run time | a request id (`u64`) | a flag: expects a response | with the message | in the response |
| **FIDL** over Zircon | a 64-bit hash of the method's fully qualified name | none: one protocol per channel | a transaction id (`u32`), 0 for one-way | transaction id 0 | with the message, up to 64 | in the response, as a result union |

They confirm two of Part 1's values in practice: D-Bus is the first real
`errors = by_name`, and Mojo's associated interfaces are `protocols =
by_binding`. They also need values Part 1 doesn't have (below).

### A shared-memory ring

`memory-ring@1` carries frames in its slots. `datagram@4`'s frames fit
unchanged, and its fixed header can be read in place in shared memory.

Handles can't cross the ring, so a frame carrying handles goes over the side
channel, and two channels lose the order between them.

**Decided 2026-11-14: a marker in the ring.** A frame with handles is sent over
the side channel, and the ring holds a small marker in its place. A receiver
reading the ring stops at a marker until the matching frame has arrived on the
side channel, then carries on. Frames without handles, the common case, cost
nothing. (A sequence number on every frame was the alternative: simpler to
reason about, but bytes on every frame.)

### Facts IPC adds

To [Part 1](dependency-protocols/capabilities.md):

| Addition | Kind | Values | Needed by |
| --- | --- | --- | --- |
| `handles` | framing fact | `none` (the framing can't carry any) · `by_transport` (the transport ties them to the frame) · `counted` (the header counts them) · `indexed` (the frame lists where each one is) | every framing over IPC; Comline's own state `by_transport`. **Adopted** into Part 1 (2026-11-14) |
| `handles_per_frame` | framing limit | a number, for framings that count or list handles | D-Bus, Binder. **Adopted** into Part 1 (2026-11-14) |
| `calls = by_hash` | a new value | a hash of the function's qualified name | FIDL |
| `errors = in_result` | a new value | errors travel in the response's payload, not the frame | Binder, Mojo, FIDL |
| `correlation = synchronous` | a new value | a reply is matched by the calling thread | Binder |

One gap needs more than a value: **instances.** A D-Bus or Binder frame names
an *object* as well as its interface, so many objects serve the same
protocol on one connection. Comline has one provider per protocol per
connection. `remote P` endpoints cover most of the need, each object
being its own channel, but a platform framing that addresses objects needs a
way to say so.

**D-Bus is the first platform framing** (decided 2026-11-14). It brings
`errors = by_name`, `handles = counted` with a `handles_per_frame` limit, and
**instances**, through object paths. Instances are therefore the next design
this needs, and no longer deferred: how a schema or a connection says which
object a call addresses, and how generated code serves several objects of one
protocol.

## Who the peer is

The OS reports the peer: its process id, user and group (`SO_PEERCRED` on
Linux), its audit token (macOS), its uid (Android Binder), its token (Windows).
Unlike anything the peer sends, the peer can't forge it.

- **Reported, not claimed:** the transport puts the identity in the
  connection's state ([Connections](connections.md#per-connection-state-and-interceptors)),
  and handlers and interceptors read it there.
- **A guarantee, when declared:** a protocol can require that a peer's identity
  is checked before any call is served. The check itself is an interceptor;
  what core guarantees is that the identity comes from the OS.

## A peer that dies

A transport that reports a peer's exit closes the connection at once: every
waiting call fails with "peer gone", instead of each waiting for its timeout.

## Versions

Processes shipped together still skew: a partial update, an old helper
process still running. The handshake stays, and IPC transports make it cheap:
one message each way, on a connection that's often reused for the process's
whole life.

## Zero copy

A `memory` handle shares a region; reading a value **in place** in it needs a
memory layout both sides agree on byte for byte. That's the exact-layout format
in [Comline for systems software](systems-software.md#an-exact-layout-format).

## Prior art

| System | What to learn |
|---|---|
| Chromium Mojo | an IDL with typed handles and endpoints (`pending_remote`, `pending_receiver`) |
| Android AIDL and HIDL, over Binder | IPC between apps, and HIDL for hardware layers: driver interfaces |
| Fuchsia FIDL, over Zircon channels | typed handles with rights; Fuchsia's drivers speak FIDL |
| D-Bus | a message bus, names and introspection |
| Windows COM and MIDL | interfaces across processes, with marshalling |
| Cap'n Proto | capabilities, and reading values in place |

## Open

- ~~**Handles**~~: decided, H2. The spellings (`file`, `memory`, `channel`,
  `remote P`, `receiver P`) are as proposed.
- **Rights** on handles: R1, R2 or R3 ([above](#rights)), settled later.
- **Which platform IPCs** get official profiles: D-Bus first (decided
  2026-11-14, [above](#facts-ipc-adds)); the order after it is open.
- **A shared-memory ring** of Comline's own, and its side channel for peer
  death.
- **Requiring a peer identity check:** how a protocol states it.
- ~~**Who ties handles to a frame**~~: decided, the transport (T1)
  ([above](#who-ties-handles-to-a-frame)).
- ~~**Forwarded endpoints**~~: decided, every child channel starts with a
  handshake ([above](#channels-handed-over-in-a-call)).
- ~~**The ring's order**~~: decided, a marker in the ring
  ([above](#a-shared-memory-ring)).
- **Instances:** how a call addresses one of several objects serving a
  protocol. Needed for D-Bus, so it's next ([above](#facts-ipc-adds)).
