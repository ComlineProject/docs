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
- **`@consumer`** names the side that calls it, and nothing more: it's the
  counterpart of `@provider` (decided 2026-10-20). When `@provider` is set,
  `@consumer` follows from it. Writing both is allowed, but a mismatch is an
  error. The other reading of the 2024 file, *how many* peers provide or
  consume (a fleet behind a reverse proxy), is dropped; if that need returns,
  it belongs with [connections](connections.md).
- **Server-to-client packets** are a protocol with `@provider = Client`. The
  client gets the dispatcher and the provider trait for it, and the server
  gets the sender.
- **`@provider = Multiple`** means both sides implement the protocol, so the
  same call can be made in either direction rather than only the server
  serving it. Examples: LSP, where the language server also sends requests to
  the editor over the same JSON-RPC connection; Bitcoin's peer-to-peer
  protocol, where both peers send `ping`, `inv` and `version`; and SSH global
  requests. Each side then generates both the dispatcher and the sender for
  that protocol. Where calls have replies, a request/reply kind marker keeps
  the two directions' request ids apart (see
  [Request ids in both directions](#request-ids-in-both-directions)).
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
- **The syntax is decided:** `@id = 0x2A`
  ([Function ids](function-ids/index.md),
  [core#127](https://github.com/ComlineProject/core/issues/127)). Ids can be
  assigned on build and written into the source, and reusing a retired id is
  an error.

### Families are protocols

A family is a protocol with an explicit **family id**, so several protocols
share one connection. That's the identifier the schema states, the choice the
[rename rules](schema-compatibility.md#renames) asked for: renaming a protocol
or namespace changes code, not the wire. Whether the family id uses the same
syntax as function ids follows from that decision.

### Phases live in the schema

A phase states which protocols are active in each direction, and which packet
moves the connection to the next phase. Both ends generate the same state
machine. The version comparison sees phases. An out-of-phase packet is a
decode error, never a misread under another phase's table. The syntax is
decided in [Phase syntax](phase-syntax/index.md): phases are an ordinary enum
marked `@phases`, and protocols and packets state their own phase and
transitions:

```ids
@phases
enum Phase {
    @initial
    Login
    Play
}

@provider = Server
@phase = Login
protocol LoginServerbound {
    @id = 0x03
    @transition = Play
    function acknowledged();
}
```

- The variant marked `@initial` is where a connection starts. A protocol with no phases has one implicit phase.
- Ids are scoped by phase, so the same id may mean different packets in
  different phases, as Minecraft's do.
- **For the version comparison,** changing a phase's tables or transitions is
  major. Adding a packet to an active protocol is minor.

#### How a connection moves between phases

Decided:

- **Phases belong to the connection.** The connection *is* the state, so
  families don't move through phases independently. A phase lists the
  families active in it, and a family can be active in several phases (a
  keepalive in every phase, say) without being duplicated.
- **The server decides when to transition,** in its own code, typically once
  some setup work is done. The client doesn't stop and wait: it carries on,
  and simply has nothing to do until the server moves it on.

Also decided (2026-10-20):

- **A transition is tied to a packet in the schema, and sending that packet
  is the transition.** It's the function marked `@transition`
  ([phase syntax](phase-syntax/enum-and-annotations.md)). Both ends then know
  the switch point. In Rust the connection can be typed by its phase: sending
  `success` consumes a `Conn<Login>` and returns a `Conn<Play>`, so
  sending a later-phase packet too early doesn't compile. TypeScript checks
  at runtime.
- **Who triggers it follows from the schema:** the transition packet's
  protocol has a `@provider`, which says which way it travels. A transition in
  a serverbound protocol is triggered by the client (Minecraft's handshake);
  one in a clientbound protocol, by the server. Nothing else is declared.
- **Each direction switches at its own point,** so neither side has to halt:
  - **The sender** switches its outgoing table right after sending the
    transition packet. Everything before it in the stream belongs to the old
    phase.
  - **The receiver** switches its incoming table on receiving it.
  - **The way back.** The receiver may already have packets in flight under
    the old phase. Its first packet in the new phase is an
    **acknowledgement**, and the sender keeps reading under the old phase
    until that arrives.
- **Whether an acknowledgement is needed is derived,** not declared: only if
  the old phase has protocols travelling back towards the sender. Minecraft's
  handshake has no clientbound packets, so the client's `hello` needs none.
- **Where the acknowledgement comes from:**
  - **Under `comline.packet@1`** the framing generates it, as a control frame
    outside the schema's id tables. Nothing is declared.
  - **Under a legacy framing** the schema names the packet that acknowledges,
    with `@acknowledges` on it. Minecraft's "login acknowledged" answers
    "login success":

    ```ids
    @provider = Client
    @phase = Login
    protocol LoginClientbound {
        @id = 0x02
        @transition = Play
        function success(session: u64);
    }

    @provider = Server
    @phase = Login
    protocol LoginServerbound {
        @id = 0x03
        @acknowledges = LoginClientbound.success
        function acknowledged();
    }
    ```

    The acknowledging packet belongs to the old phase's table, since it's
    read under it.
  - **A legacy transition that needs one and has none** is a build error,
    unless the protocol gives up an agreement guarantee with
    [`@unverified`](extensibility.md#giving-up-a-guarantee): that accepts the
    race, an in-flight packet read under the wrong table.
- **Replies still pending at a transition go first.** A transition waits until
  the replies owed to old-phase requests are sent, so they're ahead of it in
  the stream. Generated code does the waiting, not user code. A reply is
  decoded by the requester's record of its pending call, never by the phase
  table, so a reply arriving after the switch still decodes correctly.
- **A client-chosen target** is an enum field of the transition packet
  (`@transition = next`), limited by a validator
  ([phase syntax](phase-syntax/enum-and-annotations.md#as-accepted)).
- **An out-of-phase packet** is a decode error that ends the connection,
  reported as a framing fault.

### Replies: both one-way and correlated

Packet protocols do both, often within one protocol and chosen per packet:
- MQTT: QoS 0 is one-way; QoS 1 gets a `PUBACK` carrying the same id.
- Kafka: a produce with `acks=0` gets no response.
- SSH: a request carries a `want_reply` flag.
- memcached: "quiet" opcodes answer only on error.
- X11: some requests have replies and some don't, and events arrive unprompted.

Real protocols match a reply to its request in about five ways:

| How a reply is matched | Examples |
|---|---|
| **Not at all:** the "reply" is just a packet in the other direction | Minecraft's play packets, most game opcode tables (`CMSG_…` → `SMSG_…`), Bitcoin's `getdata` → `block` |
| **An id in the payload, echoed back** | Minecraft keep-alive and command suggestions (a transaction id), Bitcoin `ping`/`pong` (a nonce) |
| **An id in the header, echoed back** | DNS (16-bit id), Modbus TCP (transaction id), Kafka (`correlation_id`), MQTT (packet identifier), memcached binary (`opaque`) |
| **Implicit, by counting or order** | X11 (both sides count requests, and replies carry the sequence number), Redis (replies in request order), SSH global requests (in order) |
| **The reply's type pairs with the request's** | UDS diagnostics (response id = request id + `0x40`), Modbus (the function code echoed, `+0x80` on an error), MQTT `SUBSCRIBE` → `SUBACK` |

Decided: **both are supported.** How, split by whose protocol it is
(2026-10-20):

#### Comline's own packet framing

Decided for `comline.packet@1`, so `->` and `!` mean the same as under
datagram and JSON-RPC:

- **A function without `->` is a one-way packet,** always allowed. One-way and
  `->` functions mix freely in one family, as MQTT and Kafka mix them per
  packet: the function's signature decides.
- **How a reply is matched is a fact in the encoding's
  [profile](schema-compatibility.md#encoding-profiles):** `correlation`.
  `comline.packet@1` offers `none` or `header_id` (an id of a configurable
  width in the header), set as a
  [framing parameter](#where-the-framings-parameters-are-written).
- **Under `correlation = none`,** `->` and `!` are build errors.
- **When correlation is on, the header carries a kind marker,** request or
  reply. A reply travels in the other direction, so without it a reply's id
  could be read as a packet from that direction's table. The marker also
  settles request ids in both directions (see
  [below](#request-ids-in-both-directions)).
- **A reply's header carries a status:** ok, an error's ordinal, or a provider
  fault. That's what Comline's three outcomes need, and the closest match to
  datagram.
- **Timeouts stay client-side** (`@timeout_ms`). A reply arriving after its
  call timed out is dropped by its id.

#### Describing legacy protocols

Open, deferred until a real legacy schema needs them (the Minecraft example is
the first candidate). Each exists only to describe a protocol Comline didn't
design:

- **Payload echo** (Minecraft, Bitcoin): a function's reply declared as a
  packet in the other direction, matched on a field. For example,
  `@reply = PlayClientbound.pong` with `@match = nonce` on `ping`. The
  generated API is request and response, while the wire stays the legacy one.
- **`in_order` correlation** (Redis, SSH global requests): replies in request
  order. Simple, but one slow reply holds up the rest, and a late reply can't
  be dropped safely, so it ends the connection.
- **`sequence` correlation** (X11): both sides count requests.
- **Errors as declared packets** in the other direction (Modbus's `+0x80`),
  for headers with no room for a status.

#### Request ids in both directions

With `@provider = Multiple` both sides send requests, so two requests can
carry the same id. Existing systems handle it in one of three ways, and which
one fits depends on **what the id names and who creates it**:

| The id names… | Pattern | Used by |
|---|---|---|
| **A pending call,** living until its reply and created only by the requester | A request/reply kind marker; each side numbers its own requests | JSON-RPC 2.0 both ways (LSP), D-Bus, Cap'n Proto |
| **A stream** either side can open, with state on both | The id space split by initiator | HTTP/2 (odd/even), QUIC (low bits) |
| **A long-lived resource** referred to by the peer's handle | Per-side handles | SSH channels |

Decided: **a Comline call id names a pending call, so the kind marker is
enough.** Only the requester looks an id up, in its own table of pending
calls, so the two sides' numbers may overlap freely. No direction bit and no
id split are needed.

- `jsonrpc@1` already works this way (a message with `method` is a request).
- `comline.packet@1` gets it from the kind marker above.
- `datagram@1` implies the kind from the direction today. Allowing `Multiple`
  under it needs a kind marker in its frame, which is a new framing version.
- If Comline ever gets streams, those would need the split, as a fact of the
  framing's profile, not a per-schema choice.

### Sub-packets are tagged unions

Decided: packets whose payload is one of several shapes, picked by a sub-type
byte (an entity action that is attack, interact or interact-at; an MMO opcode
with sub-opcodes), are **one packet whose payload is a tagged union** of
structs. The second level of dispatch, hand-written in most implementations,
is generated. Unions travel untagged today, so this needs tagged unions with
explicit tag values
([core#126](https://github.com/ComlineProject/core/issues/126); how they're
written is weighed in [Tagged unions](tagged-unions/index.md)), which serve
more than packets.

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
  - correlation: none, or a header id of a given width, which adds the
    request/reply kind marker and the reply status.

  Its [profile](schema-compatibility.md#encoding-profiles) states that calls go
  by explicit id, so reordering never matters under it.

#### Where the framing's parameters are written

Leaning (recorded for discussion, not final): **named framing instances in
`config.idp`.** These extend the declared framings list
([core#117](https://github.com/ComlineProject/core/issues/117)) from plain
names to named, configured entries:

```
framings = {
    "game" = {
        encoding = "comline.packet@1"
        length = "varint"
        id = "u8"
        family = "none"
        endianness = "big"
        correlation = "none"
    }
    "rpc" = { encoding = "jsonrpc@1" }
}
```

A schema writes `@framing = "game"`, and the package's framing default can name
an instance.

Why there, and not elsewhere:

- **The parameters change the bytes,** so they belong to the producer's
  contract. They're frozen and seen by the version comparison: changing any
  of them is major. That rules out the consumer's `comline.toml`.
- **Protocols sharing a connection must agree exactly,** so the parameters are
  stated once and referenced. Writing them in each protocol's `@framing`
  value would repeat them and let copies drift.
- **One block per encoding would allow only one configuration.** A gateway
  speaking to two legacy systems needs two.
- **A `settings` default is scoped to a file or preset,** but a connection's
  framing is a package-wide contract.

How many framings a package has shapes the syntax:

| Kind of package | Framings |
|---|---|
| most | **1**: one framing throughout |
| some | **2**: say a packet framing plus a JSON-RPC admin API |
| gateways and bridges | 2 or more |

So one framing must be effortless. With one declared it's the package default
automatically, and no schema writes `@framing`. Encodings without parameters
keep the plain-list form (`framings = ["datagram@1"]`), so most packages never
write a block. There are just two forms, the list and the named map, with no
third shorthand.

Also part of it:

- **The encoding defines its parameters.** Its profile lists what each one
  accepts and which profile fact it sets: `family = "none"` means ids are
  unique across families, and `correlation = "none"` makes `->` an error.
  Third-party encodings get configurable parameters the same way.
- **The handshake covers them.** Two peers agreeing on `comline.packet@1` but
  differing in id width would misread each other, so `comline@N` hashes the
  parameters along with the name. A legacy handshake can't check them; an
  `@unverified` protocol vouches for them too.

Decided 2026-10-20 ([core#117](https://github.com/ComlineProject/core/issues/117)):

- **Instance names can't contain `@`.** Encoding names always carry
  `@version`, so the two can never collide, and `"game"` versus `"jsonrpc@1"`
  shows at a glance which kind of name it is. An instance can't shadow an
  encoding.
- **A dependency's instances are used by qualified name,** for example
  `@framing = "minecraft.game"`, so two packages speaking one legacy system
  share one definition instead of copies that drift. A change to the
  dependency's instance counts towards this package's bump by reach, as any
  dependency change does.
- **Handshake:** packet systems usually bring their own
  ([runtime#18](https://github.com/ComlineProject/runtime/issues/18)), often as
  a phase of its own. One that doesn't establish schema agreement makes the
  protocols [`@unverified`](extensibility.md#giving-up-a-guarantee).
- **Dispatch becomes phase-aware:** the active tables switch when a transition
  packet passes, on both sides at the same point.

## Open questions

- **Replies in legacy protocols:** payload echo (`@reply` / `@match`),
  `in_order` and `sequence` correlation, and errors as declared packets (see
  [Describing legacy protocols](#describing-legacy-protocols)), deferred until
  a real legacy schema needs them.
- **The framing's parameters:** leaning towards named framing instances in
  `config.idp` (see
  [Where the framing's parameters are written](#where-the-framings-parameters-are-written)).
  Instance names and sharing across packages are decided.

## Prerequisites

- **Server-to-client sending:** what `@provider = Client` needs, and nothing
  generates today. Designed in [Connections](connections.md#calls-in-both-directions).
- **Several protocols on one connection.** Designed in
  [Connections](connections.md#several-protocols-on-one-connection).
- **The handshake as a declared axis**
  ([runtime#18](https://github.com/ComlineProject/runtime/issues/18)),
  **`@unverified`** ([core#121](https://github.com/ComlineProject/core/issues/121)),
  and **encodings and their mapping**
  ([core#120](https://github.com/ComlineProject/core/issues/120)).
- **Typed annotation values**
  ([core#124](https://github.com/ComlineProject/core/issues/124)): lists and
  references for `@phase`, `@transition`, `@reply` and `@match`. Lists are
  parsed as validator calls today.
- **Settings defaults for annotations**
  ([core#125](https://github.com/ComlineProject/core/issues/125)), so a
  schema file per side or per phase states `@provider` and `@phase` once.
- **Tagged unions with explicit tags**
  ([core#126](https://github.com/ComlineProject/core/issues/126)), for
  sub-packets.

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
