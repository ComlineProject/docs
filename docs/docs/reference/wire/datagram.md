# Datagram framings

How a call and its reply are framed on a connection: `datagram@2`, the
default, and `datagram@3`, which addresses a call by wire numbers.

!!! note "`datagram@3` is available, not the default"
    The runtime ships `datagram@3`
    ([runtime#15](https://github.com/ComlineProject/runtime/issues/15)).
    It doesn't become the default until core switches to it, and the
    generators then emit wire numbers for it. Until both happen, packages
    keep `datagram@2`.

Both framings carry frames in either direction, so either end can start a
call, and several protocols can share one connection. Every frame starts
with a kind byte: `0` for a request, `1` for a reply.

**Varints** are unsigned LEB128, as in [`packed@1`](packed.md): 7 bits per
byte, low bits first, high bit set on every byte but the last. A protocol
or function number is a `u16`, so it takes 1 to 3 bytes. Only the shortest
form is accepted: `80 00` for 0 is refused, and so is a value above 65535.

## `datagram@2`

| Frame | Bytes |
|---|---|
| request | `00`, protocol (varint), call id (`u16` LE), request id (`u64` LE), arguments |
| reply | `01`, protocol (varint), request id (`u64` LE), envelope |

- The **call id** is the function's position in its protocol, and the
  **protocol** number is the protocol's position in the package. Both ends
  share them because `comline@1` refuses a peer whose IR differs.
- Reordering or inserting functions therefore changes what a call
  addresses: the profile states `calls = by_index`.

## `datagram@3`

| Frame | Bytes |
|---|---|
| request | `00`, protocol number (varint), function number (varint), request id (`u64` LE), arguments |
| reply | `01`, protocol number (varint), request id (`u64` LE), envelope (as `datagram@2`) |

- The numbers are the **wire numbers** core gives each protocol and
  function (core#127): unique in their scope, binding from `comline
  release`, and never reused once retired. Reordering or inserting
  functions doesn't move them, so the profile states `calls = by_id`.
- A reply is byte for byte a `datagram@2` reply.
- It's meant for [`comline@2`](handshakes.md#comline2), which checks
  compatibility by those same numbers.

For example, a call to function 3 of protocol 0, request id 42, with the
JSON arguments `[7,"x"]`:

```text
00 00 03 2a00000000000000 5b372c2278225d
```

Function 300 of protocol 300 is `00 ac02 ac02 …`, and 65535 is `ff ff 03`.

## The envelope

A reply's outcome, the same in both framings:

| Outcome | Bytes |
|---|---|
| ok | `00`, then the result |
| error | `01`, the error's ordinal (`u16` LE), then its body |
| fault | `02` |

## Proven by

The byte-exact vectors in the runtime's corpus:
`framing-datagram2` and `framing-datagram3`
([vectors](https://github.com/ComlineProject/runtime/tree/main/runtime/conformance/vectors)).
These include rejections: an unknown kind, overlong or out-of-range
numbers, a short request, and a reply read as a request.
