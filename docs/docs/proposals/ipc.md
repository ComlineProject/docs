# IPC

Status: **draft** · Builds on [Transports](transports.md) and
[Connections](connections.md) · Handles answer part of the open
[capabilities design](https://github.com/ComlineProject/docs/issues/98) · The
first step of [Comline for systems software](systems-software.md)

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
| **H2** | `file`, `memory`, `channel`, and endpoints of a protocol | **a type per kind of handle**, each checked on arrival | **recommended** |
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

Some systems attach rights to a handle (Zircon: read, write, map, duplicate;
Mach: send and receive rights). Whether the schema states the rights a handle
must carry, as `memory(read)` or similar, is open.

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

- **Handles:** H2 as recommended, and the spellings (`file`, `memory`,
  `channel`, `remote P`, `receiver P`).
- **Rights** on handles.
- **Which platform IPCs** get official profiles, and in what order.
- **A shared-memory ring** of Comline's own, and its side channel for peer
  death.
- **Requiring a peer identity check:** how a protocol states it.
