# Transports

Status: **draft** · Raised by [bounds on types, issue 13](type-bounds/max-only.md#issues-and-resolutions)
· Builds on [Connections](connections.md),
[Package wire defaults](package-wire-defaults.md) and the
[given-up guarantee marker](guarantee-marker/index.md)

**The question:** transports have limits of their own: a largest message, and
whether they lose, reorder or duplicate what they carry. Should a schema and a
consumer declare the transport they use, so those limits are checked before
anything runs, and if so, without making Comline harder to use?

Where things stand:

- **Rust** has a `Transport` trait that sends and receives whole frames. Its
  `max_frame()` (16 MiB by default) is checked against each outgoing frame
  before a request id is spent, so an oversized call fails alone, and a reply
  over it is answered with a fault. `InMemory` and `Tcp` (a `u32` length
  prefix) ship.
- **TypeScript** ships only an in-memory pair.
- **Configuration never names a transport.** `config.idp` states the format
  and framing (`wire = { format, framing }`); the transport is chosen in host
  code, so no check can know its limits.
- **Nothing fails silently today.** An oversized frame is refused at run time,
  and a lost reply ends in a timeout. The failures are loud, but late.
- **With every value bounded** ([issue 6](type-bounds/max-only.md#issues-and-resolutions)),
  each message has a worst-case size per format, so a transport's limit can be
  checked before run time.

## Proposal

### Optional: promised only where declared

Declaring a transport adds a new promise, **transport fit:** every call the
schema allows can be carried by the declared transport. It moves today's
run-time failures to build time.

- **Declaring is optional.** With no transport declared, nothing changes from
  today, and no give-up is needed: the schema never claimed transport fit.
- **Once declared, it's checked,** and a failure is an error unless given up
  with `@unverified = "reason"`, for example when the application splits large
  messages itself.
- **Required for a protocol that sends handles** ([IPC](ipc.md#handles)): only
  some transports carry them, so such a protocol must declare one.

This differs from validators, which are enforced by default
([issue 8](type-bounds/max-only.md#issues-and-resolutions)): a validator is a
rule the schema states, so switching it off breaks something the schema says.
A transport says nothing until someone declares it.

### Transport profiles

Each transport is a profile with stated facts, like the existing format and
framing profiles:

| Profile | Boundaries | Delivery | Order | Duplicates | Largest message |
|---|---|---|---|---|---|
| `tcp@1` | a stream, `u32` length prefix | reliable | ordered | never | `max_frame` |
| `udp@1` | messages | may lose | may reorder | possible | about 65,507 B on IPv4; a declared budget in practice (below) |
| `websocket@1` | messages | reliable | ordered | never | set by the server or library |
| `http@1` | request and response | reliable | per request | never | body limits |
| `memory` | messages | reliable | ordered | never | configured |

Later ones (QUIC, browser `postMessage`, serial, Bluetooth LE at as little as
20 bytes) follow the same shape. A third-party transport
(`com.acme.serial@1`) is unverified by Comline and goes through
`@unverified`, as third-party formats do.

### What framings need

Each framing states what it needs from a transport, and core checks the
framing's needs against the transport's facts. Proposed, to be confirmed in
each framing's specification:

| Framing | Needs |
|---|---|
| `datagram@1` (lockstep) | reliable delivery; one call at a time, so order follows |
| `datagram@2` | reliable delivery; **ordered delivery for a host that waits in order:** such a host treats "a reply that skips the innermost waiting call" as a framing error, so a reordering transport breaks it. An async host, matching replies by id, doesn't need order |
| `jsonrpc@1` | message boundaries, or a length prefix; reliable delivery |
| Packet framings ([packet dispatch](packet-dispatch.md)) | stated per framing; a packet framing may provide its own reliability |

### Who declares, and why both

| Who | Where | Why |
|---|---|---|
| **The schema's author** | `config.idp` | a protocol is designed for a medium: a UDP game protocol or a Bluetooth LE sensor protocol has sizes and loss tolerance as design constraints. Declaring them checks the schema while it's written, and tells every consumer what it was built for |
| **The consumer** | `comline.toml` | the real deployment: TCP rather than the UDP it was designed for, or a proxy with a 1 MiB limit. The checks use what's actually used, and the consumer's choice is checked against what the author designed for |

Either alone falls short: the author can't know the deployment, and a consumer
alone could find a schema unusable on its intended medium only at deployment.

Illustrative only; the keys aren't settled:

```ids
// config.idp: what the protocol is designed for
wire = { format = "packed@1", framing = "datagram@2", transport = "udp@1" }
```

```toml
# comline.toml: what this consumer actually uses
[transport]
name = "udp@1"
max_message = 1200
```

### Each side's limit

A request must fit the client's sending limit and the server's receiving limit;
a reply, the reverse.

- **Now:** each side checks its own limit, since limits aren't exchanged.
- **Later:** a handshake version exchanges them, so both sides are checked when
  connecting. A `comline@2` handshake is already under discussion
  ([runtime#67](https://github.com/ComlineProject/runtime/issues/67)).

### A budget, not discovery

A path's MTU can change while a connection runs.

- **A declared budget** is a fixed size, such as 1200 bytes, which QUIC also
  assumes every path carries. What's checked at build holds at run time.
- **Discovery** finds the real MTU while running; it can fall mid-connection,
  making a message that was valid when connecting undeliverable.

So the budget is declared, and discovery may only ever **raise** what's used
above it, never lower the promise.

### Loss, reordering and duplicates

In scope, through the facts above:

- **Loss** means timeouts, and a call happens at most once. Retrying risks
  running a call twice. What loss does to each return form (one-way, quiet,
  acknowledged) is in [Return forms](return-forms.md#what-each-transport-changes).
- **Duplicates** are filtered by request id, by the framing or the core.
- **Over an unreliable transport,** reliability comes from the framing
  (acknowledgements, as a packet framing might provide) or from the transport
  (as QUIC does). Core checks that one of them provides it, or that it's given
  up.

### At run time

Generated code passes the declared transport and each protocol's worst-case
message size to the connection. The shared runtime core compares them with the
real transport's `max_frame()` when the connection is set up, and refuses a
mismatch unless it's given up.

### Language server

Hover shows the fit, resolved from the schemas, `config.idp` and the consumer's
configuration: "fits `udp@1` (1200 B): worst case 980 B", or which call
doesn't fit and by how much.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Declaring a transport is mandatory | requires a declaration everywhere, even where nothing is claimed; restrictive for no guarantee gained |
| Only the consumer declares | a schema can be unusable on its intended medium, found only at deployment |
| Only the author declares | can't see the deployment: a different transport, or a proxy's limit |
| Discovering MTU instead of a budget | a promise checked at build could stop holding mid-connection |

## Open

- **The keys:** where exactly in `config.idp` and `comline.toml`, and whether
  per protocol or per package.
- **Profile names and versions:** which profiles are official, and their facts.
- **Each framing's needs:** confirmed in each framing's specification.
- **Reliability over unreliable transports:** whether Comline provides a
  framing with acknowledgements, or requires a reliable transport.
- **Retries:** whether calls can be marked safe to repeat, so a framing may
  retry them.
- **Streams** ([an open design](https://github.com/ComlineProject/docs/issues/98)):
  how a stream relates to a transport's largest message.
