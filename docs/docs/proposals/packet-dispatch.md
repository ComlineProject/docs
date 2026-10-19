# Packet dispatch: families, ids and phases

Status: **under discussion** · tracked in
[core#123](https://github.com/ComlineProject/core/issues/123) · partly decided,
nothing implemented

**The question:** how Comline describes **message-oriented packet protocols**,
the slim systems that typically come from C, and generates their dispatch. In
those systems, a header identifies each packet by an id, often within a family
or group. Both sides know every table ahead of time, and the tables often
change with the connection's **phase** and **direction**. Such a system has its
own framing, handshake and dispatch, so it's its own encoding with its own
identifier, as different from JSON-RPC as JSON-RPC is from datagram.

## The shape of packet systems

They vary along independent axes:

| Axis | Variants | Seen in |
|---|---|---|
| **Id space** | one flat opcode table; a family (group) plus an id; ids scoped to a phase; ids scoped to a direction | Game servers use flat or grouped opcode tables. Minecraft scopes ids by connection state (handshake, status, login, configuration, play) **and** by direction, so `0x00` means a different packet in each. SSH reserves number ranges per layer. TLS has a content type plus a handshake type. |
| **Phase** | none; a state machine where certain packets move the connection to the next phase, which swaps the active tables | a login-success packet moving the connection to play |
| **Direction** | both sides send unprompted, often with separate tables per direction | server pushes are the norm, not a special case |
| **Correlation** | none (a reply is just another packet); a sequence number; a request id | many games use none |
| **Header** | a length prefix (fixed width or varint), id width, a family byte, flags, a sequence, endianness | every system has its own layout |
| **Handshake** | the system's own version or hello packet, often a phase of its own | |

## Where Comline stands

1. **Only the client sends unprompted.** Calls go from client to server, and
   one-way functions exist only in that direction. Server push is listed as
   undesigned in the [target contract](../design/core-target-contract.md).
2. **Function ids are implicit.** Datagram addresses a call by the function's
   position in its protocol. Packet systems need **explicit, fixed, possibly
   sparse** ids, because those ids *are* the contract.
3. **A connection serves one protocol,** so there are no families.
4. **There are no phases.**
5. **A framing can't read addressing from the schema.** Under
   [the extensibility proposal](extensibility.md#what-a-format-cant-be), a
   framing that needs more than the generated data model is a language feature,
   and packet addressing is exactly that.

## The approach: addressing in the schema, bytes in the framing

**Addressing** is the family, the id, the direction and the phase. It goes in
the schema: both ends must agree on it, so it's part of the contract and of the
[version comparison](schema-compatibility.md). Generators turn it into
**dispatch tables**, mapping (phase, direction, family, id) to a decoder and a
handler, plus the phase transitions. **A framing only lays out the header
bytes,** looking ids up in those tables. A legacy system's exact header is then
a small custom framing, not a fork of Comline.

## Decided so far

### Direction: `@provider` and `@consumer`

From the 2024 proposal (`proposals/idl/protocol_provider_and_provenance.ids`),
and already used in `runtime-std-extra`'s `reverse_proxy.ids`:

- **`@provider`** (`Server`, `Client` or `Multiple`) names the side that
  **implements** a protocol. That's the runtime's existing sense of
  "provider": the provider trait, provider faults.
- **`@consumer`** names the side that calls it.
- **Server-to-client packets** are a protocol with `@provider = Client`. The
  client gets the dispatcher and the provider trait for it, and the server
  gets the sender.
- Core doesn't recognise `@provider` today: it parses and is ignored. It
  becomes a known annotation.

```ids
@provider = Server
protocol LoginServerbound {
    function hello(protocol_version: u32, name: string);
    function acknowledged();
}

@provider = Client
protocol LoginClientbound {
    function success(session: u64);
    function rejected(reason: string);
}
```

### Explicit ids, available everywhere

- Any function may state its id. A packet framing **requires** ids. Datagram
  uses them when present, which makes reordering functions harmless there too.
- Ids are written in decimal or hex. Integer literals are decimal-only today,
  so hex needs a small grammar addition, useful for constants as well.
- Ids are unique within a family and direction.
- In the version comparison, changing an id is major, and adding a function
  with a new id is minor.
- **The syntax is open:** [Function ids](function-ids/index.md) weighs an
  `@id` annotation against the original `1# function` prefix.

### Families are protocols

A family is a protocol with an explicit **family id**, so several protocols
share one connection. That's the identifier the schema states, the choice the
[rename rules](schema-compatibility.md) asked for: renaming a protocol
or namespace changes code, not the wire. Whether the family id uses the same
syntax as function ids follows from that decision.

### Phases live in the schema

A phase states which protocols are active in each direction, and which packet
moves the connection to the next phase. Both ends generate the same state
machine. The version comparison sees phases. An out-of-phase packet is a
decode error, never a misread under another phase's table. One possible
shape, with the syntax open:

```ids
phase Login {
    serverbound: [LoginServerbound]
    clientbound: [LoginClientbound]
    LoginClientbound.success -> Play
}

phase Play {
    serverbound: [Movement, Chat]
    clientbound: [World, Chat]
}
```

- The first phase declared (or one marked initial) is where a connection
  starts. A protocol with no phases has one implicit phase.
- Ids are scoped by phase, so the same id may mean different packets in
  different phases, as Minecraft's do.
- **For the version comparison,** changing a phase's tables or transitions is
  major. Adding a packet to an active protocol is minor.

### The mechanism, plus an official framing

- **For anyone:** addressing in the schema and generated dispatch tables. A
  custom framing (`com.acme.legacy@1`, mapped per target as in
  [the extensibility proposal](extensibility.md#how-generated-code-reaches-one))
  reads them.
- **Official:** `comline.packet@1`, a configurable header covering the common
  layouts:
  - a length prefix: none, `u16`, `u32` or varint;
  - an id width;
  - a family width, or none;
  - endianness;
  - an optional sequence number.

  Its [profile](schema-compatibility.md#encoding-profiles) states that calls go
  by explicit id, so reordering never matters under it.
- **Handshake:** packet systems usually bring their own
  ([runtime#18](https://github.com/ComlineProject/runtime/issues/18)), often as
  a phase of its own. One that doesn't establish schema agreement makes the
  protocols [`@unverified`](extensibility.md#giving-up-a-guarantee).
- **Dispatch becomes phase-aware:** the active tables switch when a transition
  packet passes, on both sides at the same point.

## Open questions

- **Phase syntax and transition semantics.** Exactly when does each side
  switch: after sending, after receiving, or after an acknowledgement? Can a
  transition be triggered from either direction? Are phases per connection, or
  can families move through phases independently?
- **Replies in packet mode.** A function with `->` needs to match a reply to its
  request: a request id or a sequence in the header. Or packet protocols could
  be one-way only, with replies modelled as packets in the other direction,
  which is how most packet systems actually work.
- **The official framing's parameters.** Where are they stated: on the framing
  name, in `config.idp`, or in `@framing`'s value?
- **`@consumer`.** What does it add beyond being the provider's complement? The
  original note says the parameters "need more situational introspection". And
  what does `Multiple` mean on a single connection: both peers implementing the
  same protocol, peer-to-peer?
- **The family id's syntax,** which follows the function-id decision.

## Prerequisites

- **Server-to-client sending:** what `@provider = Client` needs, and nothing
  generates today.
- **Several protocols on one connection,** listed as open in the target
  contract.
- **The handshake as a declared axis**
  ([runtime#18](https://github.com/ComlineProject/runtime/issues/18)),
  **`@unverified`** ([core#121](https://github.com/ComlineProject/core/issues/121)),
  and **encodings and their mapping**
  ([core#120](https://github.com/ComlineProject/core/issues/120)).

## What it touches

- **core:**
  - `@provider` and `@consumer` as known annotations;
  - explicit ids, and hex integer literals;
  - family ids;
  - the phase declaration;
  - rules in the version comparison.
- **generation**, **comline-rust** and **comline-typescript:**
  - dispatch tables;
  - provider and consumer sides per protocol;
  - phase-aware dispatchers.
- **runtime:**
  - several protocols per connection;
  - server-to-client sending;
  - `comline.packet@1` with its profile and vectors.
- **language server:** completion and checks for ids, families and phases.
- **docs:** a guide to describing a packet protocol.
