# `datagram@4`

Status: **accepted** (2026-11-14) with [Proposal A](multi-package-connection.md),
the fixed-width layout to be confirmed by benchmark · See
the [section overview](index.md)

`datagram@4` is a binary framing for a connection that carries protocols from
**one or more packages**, with calls in both directions. A request names its
protocol by a **connection number** that the handshake binds, and its
function by the function's **wire number**. Both numbers are stable, so
inserting or reordering declarations never changes what a call addresses, and
two packages' protocols never collide. Every header field is **fixed-width**
and at a fixed offset.

## Requirements

- **A handshake that binds connection numbers** (`binds = protocols`):
  [`comline@3`](multi-package-connection.md#the-handshake-comline3). With no
  handshake, or one that binds nothing, there are no connection numbers, and
  the build refuses the pairing.
- **Wire numbers** for every function: core's numbering, from the package's
  build history ([Number](../../reference/versioning.md#number)). Each
  function's number comes from the history of the package that declares its
  protocol.
- **A transport that delimits frames.** Each transport message is exactly one
  frame. Over TCP, the runtime's stream transport writes a `u32` LE length,
  then the frame. A frame is held to the transport's limit, 16 MiB by default
  in every runtime.
- **Any format.** The payload is opaque bytes, so any format whose `output`
  is `bytes` or `json` fits.

## Numbers

Every number is little-endian, at a fixed width:

| Number | Width | Meaning |
| --- | --- | --- |
| connection number | `u16` | the protocol's number on this connection, as the handshake binds it. Under `comline@3`, it's the protocol's position in the initiator's Hello. Packages are listed by ascending id and protocols by ascending wire number, so the first protocol listed is 0 |
| function number | `u16` | the function's wire number in its protocol, from its package's history: unique in the protocol, and never reused once retired |
| request id | `u32` | chosen by the caller, sequentially (see [Request ids](#request-ids)) |
| error ordinal | `u16` | the error's position in the error space of the schema that declares the protocol |

## Frames

Every frame starts with a **kind** byte, which decides the rest of its
layout. Any other value is malformed.

| Kind | Frame | Header |
| --- | --- | --- |
| `00` | request, expecting a reply | 9 bytes |
| `01` | reply | 7 bytes |
| `02` | one-way request | 5 bytes |

### Request (`00`)

| Offset | Field | Bytes | Meaning |
| --- | --- | --- | --- |
| 0 | kind | `00` | a request that expects a reply |
| 1 | protocol | `u16` LE | the connection number of the protocol called into |
| 3 | function | `u16` LE | the function's wire number in that protocol |
| 5 | request id | `u32` LE | the id its reply will carry |
| 9 | arguments | the rest of the frame | the function's arguments, in declaration order, encoded by the connection's format as one value |

### One-way request (`02`)

| Offset | Field | Bytes | Meaning |
| --- | --- | --- | --- |
| 0 | kind | `02` | a request that gets no reply |
| 1 | protocol | `u16` LE | as above |
| 3 | function | `u16` LE | as above |
| 5 | arguments | the rest of the frame | as above |

A function declared without `->` is one-way, and is always called with kind
`02`. Since nothing will answer, it carries no request id. A function declared
with `->` is always called with kind `00`. A request whose kind disagrees with
its function's declaration is answered as a call the receiver doesn't have
(see [Receiving](#receiving)).

### Reply (`01`)

| Offset | Field | Bytes | Meaning |
| --- | --- | --- | --- |
| 0 | kind | `01` | a reply |
| 1 | protocol | `u16` LE | the connection number of the request it answers |
| 3 | request id | `u32` LE | the id of the request it answers |
| 7 | outcome | the rest of the frame | one of the three below |

The **outcome:**

| Outcome | Bytes | Meaning |
| --- | --- | --- |
| ok | `00`, then the result | the function's return value, encoded by the connection's format. A function declared `-> ()` returns the format's empty value |
| error | `01`, the error ordinal (`u16` LE), then its body | an error from the function's `!` list. The body is the error's fields, encoded like a struct |
| fault | `02`, nothing after | the provider failed in a way the schema doesn't describe, or couldn't take the call |

The reply's protocol isn't needed to match it, since the request id does that.
It's there so a reply can be attributed to its protocol from the frame alone,
in a capture or a log, and so a reply that names the wrong protocol shows up
as a bug.

## Request ids

- **Per direction.** Each end numbers the requests it sends. Both ends can use
  the same id at once without confusion, because a reply always answers a
  request of the end that receives it.
- **Sequential.** Each end starts at 0 and adds 1 per request expecting a
  reply, wrapping from 4294967295 to 0. A caller that gives up on a request,
  for example after a timeout, doesn't reuse its id until the counter wraps.
  So a late reply can't be mistaken for a newer request's.
- **Matched by id.** A reply is matched to its request by request id. Its
  protocol must be the request's.

## Receiving

| Received | What the receiver does |
| --- | --- |
| a frame that doesn't parse: unknown kind, or shorter than its kind's header | ends the connection: it's malformed |
| a request (`00`) for a protocol this end provides, to a request/response function it has | dispatches it, and replies |
| a one-way request (`02`) for a protocol this end provides, to a one-way function it has | dispatches it. It never replies |
| a request (`00`) it can't take: an unbound connection number, a protocol it doesn't provide or the handshake refused, a function the protocol doesn't have, or a one-way function | replies with a **fault** |
| a one-way request (`02`) it can't take, for the same reasons, or to a request/response function | drops it, and never replies |
| a reply whose request id awaits no reply, such as a late reply to a request its caller gave up on | drops it |
| a reply whose protocol isn't its request's, or whose outcome tag isn't `00`, `01` or `02` | ends the connection: it's malformed |
| an error ordinal the caller's schema doesn't have | gives the caller a remote error with that ordinal: the provider is newer |

A well-behaved caller never sends the fourth and fifth rows. After the
handshake, a call to a function or protocol the peer lacks fails locally,
without reaching the wire.

## Limits

What the frame's widths allow. Stated in the [profile](#profile) as
[limits](capabilities.md#limits), and checked at build:

| Limit | Value | From |
| --- | --- | --- |
| protocols per connection | 65536 | the `u16` connection number |
| functions per protocol | 65536 | the `u16` function number, as core's wire numbers |
| errors per schema | 65536 | the `u16` error ordinal |
| requests awaiting a reply, per direction | 4294967296 | the `u32` request id |

The largest frame isn't the framing's limit. It's the transport's.

## Examples

A connection carrying `localdeps` (whose `greeting::Foo` is its protocol #0)
and `test` (whose `none::Thing` is its protocol #0). If `localdeps`'s id
sorts first, `Foo` is bound to 0 and `Thing` to 1. Arguments are in `json@1`.

A call to `Thing`'s function 3, request id 42, arguments `[7,"x"]`:

```text
00 0100 0300 2a000000 5b372c2278225d
```

A call to `Foo`'s function 0, request id 43, the same arguments:

```text
00 0000 0000 2b000000 5b372c2278225d
```

A one-way call to `Thing`'s function 5, with no arguments (`[]`):

```text
02 0100 0500 5b5d
```

Replies to the first call: ok with `7`, error 2 with an empty body, and a
fault:

```text
01 0100 2a000000 00 37
01 0100 2a000000 01 0200 7b7d
01 0100 2a000000 02
```

Function 65535 of connection number 300 is `00 2c01 ffff …`.

## Profile

```json
{
  "name": "datagram@4",
  "kind": "framing",
  "facts": {
    "calls": "by_id",
    "protocols": "by_binding",
    "directions": "both",
    "errors": "by_ordinal",
    "payload": "opaque"
  },
  "limits": {
    "protocols_per_connection": 65536,
    "functions_per_protocol": 65536,
    "errors_per_schema": 65536,
    "pending_requests": 4294967296
  }
}
```

(The profile in the corpus gives each fact and limit with `value` and
`proven_by`.) The facts and limits are [described here](capabilities.md#proposed-facts).
The profile is fixed: a change to any of them would be `datagram@5`.

## Pros and cons

### Pros

- **Several packages on one connection,** with no registry of ids across
  packages. Two packages' protocol #0 never collide.
- **Stable addresses.** Inserting, reordering or renaming functions and
  protocols never changes what a call addresses.
- **Fixed headers.** Every field is at a fixed offset. A receiver checks a
  frame's length against its kind's header once, then reads each field with a
  plain load, with no per-byte branches and no shortest-form or range checks.
  Packet filters, eBPF and XDP programs, load balancers and dissectors can
  match a protocol or function at a fixed offset.
- **Dense protocol numbers.** Connection numbers run 0, 1, 2…, so a receiver
  dispatches with an array index.
- **Small headers.** A request is 9 bytes, a one-way request 5, and a reply 7.
- **One-way calls are on the wire.** A receiver stays silent for a one-way
  call it can't take, so a misbehaving peer can't trigger a reply nobody
  awaits.
- **Late replies are harmless.** Sequential request ids and dropping
  unmatched replies let a caller time out without ending the connection.

### Cons

- **Frames aren't self-describing.** A capture or log of frames can't be read
  without the connection's Hello, because the same connection number means
  different protocols on different connections. Debugging and tracing tools
  need the handshake, not just the packages' facts.
- **Frames can't be forwarded as they are.** A proxy relaying calls between
  two connections that carry different package sets must rewrite the
  protocol number in every request and reply.
- **No numbers at build time.** Generated code resolves a protocol after the
  handshake. A sender caches it once per connection, so the per-call cost is
  small, but it's no longer a constant the compiler folds.
- **Larger than varints for small numbers.** A request below 128 protocols
  and functions would be 2 bytes shorter with varints.
- **Fields are unaligned.** The kind byte puts every field at an odd offset.
  Every common target reads unaligned integers, but a strict-alignment target
  has to copy them out first.
- **`u16` ceilings.** 65536 protocols per connection and functions per
  protocol. Core's wire numbers have the same ceiling, so the framing adds no
  new one.
- **The reply's protocol is redundant** for matching. It costs 2 bytes per
  reply, kept for attribution and checking.
- **A request's kind must match its function's declaration.** A mismatch is
  a bug that's caught, not one that's tolerated.

### Why fixed widths

Varints were considered for the connection and function numbers, and
rejected:

| Layout | Request | One-way | Reply | Fields at fixed offsets |
| --- | --- | --- | --- | --- |
| Varint numbers, `u64` id | 11 to 15 bytes | (not marked) | 10 to 12 bytes | the kind only |
| Fixed `u16`s, `u64` id | 13 bytes | (not marked) | 11 bytes | all |
| **Fixed `u16`s, `u32` id, one-way kind (chosen)** | **9 bytes** | **5 bytes** | **7 bytes** | **all** |
| Same, with no protocol in replies | 9 bytes | 5 bytes | 5 bytes | all |

- **Varints** put every later field at a variable offset. They need
  shortest-form and range checks on every frame, and their decoder's
  branches predict poorly once numbers pass 127. In return they save 2 bytes
  per request, and nothing at all once numbers pass 127.
- **A `u32` request id** saves 4 bytes on every request and reply, more than
  varints would. 2³² requests in flight per direction is more than any
  connection will have, and sequential ids make the wrap safe.
- **The one-way kind** saves the request id on one-way calls, and closes a
  hazard: without it, a receiver can't tell a call is one-way, answers an
  unknown one with a fault, and the caller receives a reply to nothing.
- **The reply's protocol** stays, for the reasons [above](#reply-01).

The choice should still be confirmed by measurement. The runtime's
[benchmark gates](../shared-runtime-core/verification.md) can time encoding,
decoding and dispatch for this layout beside `datagram@3`, at small and large
numbers.

## What it can't do

- **Address a protocol before the handshake.** Connection numbers exist only
  once the handshake has bound them. Generated code names a protocol by its
  package id and wire number, and looks up the connection number after
  connecting.
- **Run without a binding handshake.** It requires `comline@3`, so it can't
  be paired with `none`.
- **Report which request it couldn't read.** A malformed frame ends the
  connection.
- **Exceed its [limits](#limits).**
- **Stream, cancel or fragment.** One request has one reply at most, and one
  frame has one message. Each must fit the transport's frame limit.
- **Order calls.** The framing says nothing about order. The connection
  decides it (by default, one call at a time per connection).

## Proven by

`framing-datagram4` vectors in the runtime's corpus, byte-exact:

- a request, a one-way request and each reply outcome;
- numbers at 0, 255, 256 and 65535, and request ids at 0 and 4294967295;
- two packages whose protocols are both #0, called on one connection under
  their connection numbers (`protocols = by_binding`, with
  `handshake-comline3`);
- rejections: unknown kind, a frame shorter than its header for each kind, a
  reply with an unknown outcome tag, and a reply naming the wrong protocol;
- a request to an unbound connection number, answered with a fault; a one-way
  request to one, answered with nothing; a reply to no pending request,
  dropped;
- the request id wrapping from 4294967295 to 0.
