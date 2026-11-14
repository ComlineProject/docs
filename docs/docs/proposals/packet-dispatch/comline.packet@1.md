# `comline.packet@1`

Status: **draft** · the official packet framing of
[Packet dispatch](index.md#the-mechanism-plus-an-official-framing) · its
parameters' facts and limits are [decided there](index.md#what-each-parameter-sets) ·
its layout [decided](#as-decided) 2026-11-14, tracked in
[core#123](https://github.com/ComlineProject/core/issues/123) ·
moves to the [framings reference](../../reference/wire/framings/index.md)
once built

`comline.packet@1` is Comline's configurable framing for **packet protocols**:
packets addressed by explicit ids, optionally grouped into families, with
phases, in both directions, with or without replies. One framing covers the
common header layouts through its parameters. A protocol Comline didn't
design, whose header no combination of parameters matches, gets a framing of
its own instead ([Packet dispatch](index.md#describing-legacy-protocols)).

## Parameters

Written in a named framing instance in `config.idp`
([where](index.md#where-the-framings-parameters-are-written)):

```idp
framings = {
    "game" = {
        encoding = "comline.packet@1"
        length = "varint"
        family = "u8"
        id = "u8"
        endianness = "little"
        correlation = { header_id = "u32", status = "u16" }
    }
}
```

| Parameter | Values | Default | Controls |
| --- | --- | --- | --- |
| `length` | `none`, `u16`, `u32`, `varint` | `u32` | the length prefix; `none` leaves frames to the transport |
| `family` | `none`, `u8`, `u16` | `u8` | the family field; `none` makes ids unique across the phase's protocols |
| `id` | `u8`, `u16`, `u32`, `varint` | `u16` | the packet id field |
| `endianness` | `little`, `big` | `little` | every fixed-width integer in the header |
| `correlation` | `none`, or `{ header_id = "u16" \| "u32", status = "u8" \| "u16" }` | `none` | replies: the kind byte, the correlation id and the status |

Every parameter is in the parameter hash, so two peers that differ in any of
them are refused by a handshake that checks encodings.

## Requirements

- **Explicit ids.** Every packet has an `@id`, and every protocol has one as
  its family id unless `family = "none"`. The build refuses a packet without
  one.
- **Ids that fit.** Each id fits its field, as the
  [limits](#limits) state, checked at build.
- **Unique ids.** Ids are unique per phase and direction: among a family's
  packets, or under `family = "none"`, among every packet active in the phase
  and direction.
- **A transport.** With `length = "none"` the transport must delimit frames.
  Otherwise any byte stream will do.
- **Any format** whose `output` is `bytes` or `json`. The payload is opaque.

## Integers

- **Fixed-width** fields (`u8`, `u16`, `u32`) are in the instance's
  `endianness`. That covers the length prefix, family, id, correlation id and
  status.
- **`varint`** fields are unsigned LEB128, always low bits first, whatever the
  `endianness`. Only the shortest form is accepted, and a value above the
  field's limit is malformed. Minecraft's VarInt reads the same way for
  non-negative values.
- **The payload isn't affected.** It's encoded by the connection's format,
  with the format's own byte order (`packed@1` is little-endian). A legacy
  big-endian payload needs a big-endian format, not this parameter.

## Frames

A frame is a header followed by a payload. The header's fields come in this
order, each only when its parameter puts it there:

| # | Field | Present when | Width |
| --- | --- | --- | --- |
| 1 | length | `length` isn't `none` | `length` |
| 2 | kind | `correlation` isn't `none` | 1 byte |
| 3 | family | `family` isn't `none`, and the frame is a packet (not a reply) | `family` |
| 4 | id | the frame is a packet (not a reply) | `id` |
| 5 | correlation id | the frame is a request or a reply | `header_id` |
| 6 | status | the frame is a reply | `status` |

**The length** counts every byte after the length field itself, so a reader
knows where the frame ends before reading anything else.

### Kinds

Under `correlation = none` there's no kind byte. Every packet is one-way, and
replies don't exist.

With correlation, the kind byte says what the frame is:

| Kind | Frame | Fields after the kind |
| --- | --- | --- |
| `00` | request: a packet whose function has `->` | family, id, correlation id, arguments |
| `01` | reply | correlation id, status, outcome body |
| `02` | one-way packet: a function without `->` | family, id, arguments |
| `03` | control frame | control code, its body |

A packet's kind must match its function's declaration. A mismatch is
malformed.

### Replies

A reply names no family and no id. It's matched to its request by the
correlation id alone, and decoded by the requester's record of that request,
never by the phase's tables. So a reply that arrives after a phase transition
still decodes ([Packet dispatch](index.md#how-a-connection-moves-between-phases)).

**The status** is the reply's outcome:

| Status | Outcome | Body |
| --- | --- | --- |
| 0 | ok | the result, encoded by the format |
| 1 | fault | nothing |
| 2 and up | the error with ordinal *status − 2* | the error's fields, encoded like a struct |

A `u8` status allows 254 errors, and a `u16` 65534.

### Correlation ids

Each end numbers its own requests, starting at 0 and adding 1 per request,
wrapping at the width's maximum. Replies travel the other way, so the two
ends' numbers may overlap freely. A caller that gives up on a request doesn't
reuse its id until the counter wraps. A reply to no pending request is
dropped, which is what a late reply after a timeout is.

### Control frames

Frames the framing sends itself, outside the schema's id tables. There's one
today: the **phase acknowledgement**, the first frame a receiver sends in a new
phase, when the old phase had packets travelling back
([Packet dispatch](index.md#how-a-connection-moves-between-phases)).

| Field | Bytes | Meaning |
| --- | --- | --- |
| control code | `00` | phase acknowledgement |
| phase | varint | the phase entered: its variant's position in the `@phases` enum |

How a control frame is told apart depends on the instance:

- **With correlation:** kind `03`.
- **Without correlation:** the **largest value of the family field** marks a
  control frame (`0xFF` under `family = "u8"`), with no id after it. Under
  `family = "none"`, the **largest value of the id field** does. That value is
  reserved, so the [limits](#limits) are one lower.
- **Under `id = "varint"` with `family = "none"`** there's no largest value.
  Value 0 is reserved instead, and ids start at 1.

An acknowledgement for a phase other than the one the sender just entered is
malformed.

## Layouts at a glance

| Instance | One-way packet | Request | Reply |
| --- | --- | --- | --- |
| Minecraft-like: `length = varint`, `family = none`, `id = varint`, no correlation | len (varint) + id (varint) + payload | (none) | (none) |
| Game opcodes: `length = u16`, `family = u8`, `id = u8`, no correlation | 2 + 1 + 1 = **4 bytes** | (none) | (none) |
| RPC over packets: `length = u32`, `family = u8`, `id = u16`, `header_id = u32`, `status = u16` | 4 + 1 + 1 + 2 = **8 bytes** | 4 + 1 + 1 + 2 + 4 = **12 bytes** | 4 + 1 + 4 + 2 = **11 bytes** |
| Over a message transport: `length = none`, `family = u8`, `id = u8`, `header_id = u16`, `status = u8` | 1 + 1 + 1 = **3 bytes** | 1 + 1 + 1 + 2 = **5 bytes** | 1 + 2 + 1 = **4 bytes** |

For example, the game-opcode instance (little-endian) sending family 2's
packet `0x10` with a 3-byte payload `aa bb cc`:

```text
0500 02 10 aabbcc
```

The RPC instance replying to request 7 with error ordinal 1 and an empty
`packed@1` body:

```text
07000000 01 07000000 0300
```

## Receiving

| Received | What the receiver does |
| --- | --- |
| a frame that doesn't parse: a short header, an overlong or out-of-range varint, an unknown kind, a length past `frame_bytes` | ends the connection: it's malformed |
| a length prefix that disagrees with the frame the transport delivered | ends the connection: it's malformed |
| a packet whose family and id are active in this phase and direction | dispatches it; a request gets a reply |
| a packet whose family or id isn't active in this phase and direction | ends the connection: an out-of-phase or unknown packet is a decode error ([decided](index.md#how-a-connection-moves-between-phases)) |
| a packet whose kind disagrees with its function (`00` for one-way, `02` for `->`) | ends the connection: it's malformed |
| a reply whose correlation id awaits no reply | drops it |
| a reply with a status past the caller's known errors | gives the caller a remote error: the provider is newer |
| a control frame with an unknown code, or an acknowledgement for the wrong phase | ends the connection: it's malformed |

Unlike `datagram@4`, an unknown packet ends the connection instead of getting
a fault. A packet system's tables are fixed and agreed, so an unknown id means
the two ends are out of step, and nothing after it can be trusted.

## Profile

Its facts and limits depend on the parameters
([decided in Packet dispatch](index.md#what-each-parameter-sets)), stated in
[Part 1](../dependency-protocols/capabilities.md)'s terms:

| Fact | Value |
| --- | --- |
| `calls` | `by_id` |
| `protocols` | `by_id`, or `in_call` under `family = "none"` |
| `directions` | `both` |
| `errors` | `by_ordinal` |
| `payload` | `opaque` |
| `correlation` | `none` or `header_id` |
| `one_way` | `in_frame` with correlation (kind `02`). Without it every packet is one-way |
| `handles` | `none` |

### Limits

| Limit | Value |
| --- | --- |
| `protocols` | 2⁸ or 2¹⁶ per package, by `family`, one less without correlation (a control value) |
| `functions_per_protocol` | 2⁸, 2¹⁶, or core's 2¹⁶ for `u32` and `varint`, by `id`. One less when the id field carries the control value. Under `family = "none"`, this caps all packets in a phase and direction together |
| `errors_per_schema` | 254 or 65534, by `status` |
| `pending_requests` | 2¹⁶ or 2³² per direction, by `header_id` |
| `frame_bytes` | 65535 or 4294967295 by `length` (the length counts the bytes after itself), or the transport's |

## What it can't do

- **Describe another system's header** unless a combination of parameters
  matches it exactly. Minecraft-style headers fit, and most others need a
  framing of their own.
- **Answer an unknown packet.** It ends the connection.
- **Carry several packages by binding.** Ids are fixed in the schema. A
  dependency's packets join only when the build proves their ids disjoint
  ([Packages on a packet connection](index.md#packages-on-a-packet-connection)).
- **Carry handles.**
- **Stream, cancel or fragment** a packet.

## Proven by

`framing-packet1` vectors, byte-exact, for each parameter value at least once:

- every field at its widths and both byte orders, and varints at 127, 128,
  16383 and 16384;
- each kind, each status outcome, and each control frame, in instances with
  and without correlation and family;
- rejections: short headers, overlong varints, unknown kinds, a mismatched
  length, a packet's kind disagreeing with its function, an out-of-phase
  packet, an acknowledgement for the wrong phase;
- correlation ids wrapping, and a late reply dropped;
- each limit at its maximum, and the reserved control value refused as a
  packet id.

## As decided

Decided 2026-11-14, each as written above:

| | Question | Decided | Alternatives weighed |
| --- | --- | --- | --- |
| **P1** | Header field order | length, kind, family, id, correlation id, status | kind before length; correlation id before family and id |
| **P2** | How a control frame is told apart without correlation | the largest family value, or the largest id value under `family = "none"`; value 0 under a varint id | a kind byte on every frame (1 byte per packet); a kind byte only when the schema has acknowledged transitions (the layout then depends on the schema) |
| **P3** | One-way packets under correlation | their own kind, `02`, with no correlation id | kind `00` with a correlation id nobody answers |
| **P4** | Whether a reply names its family and id | no: matched by correlation id, decoded by the requester's record | yes, as `datagram@4` keeps its protocol: attributable in captures, 2–6 bytes more per reply |
| **P5** | Status values | 0 ok, 1 fault, 2 and up errors | 0 ok, errors from 1, the largest value fault |
| **P6** | What `endianness` covers | every fixed-width header integer, the length included; never varints or the payload | the length prefix fixed little-endian; or the payload's format too |
| **P7** | An unknown packet in the active phase | ends the connection, as an out-of-phase one does | a fault reply for a correlated request, ending the connection only for one-way packets |
| **P8** | Correlation ids | sequential per direction, wrapping; late replies dropped | any id unique among pending requests |
| **P9** | Defaults | `length = u32`, `family = u8`, `id = u16`, `little`, no correlation | no defaults: every parameter written out in each instance |
