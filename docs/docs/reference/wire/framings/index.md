# Framings

How a call and its reply are framed on a connection: `datagram@3`, the
default, which addresses a call by wire numbers, and `datagram@2`, which
addresses it by position.

Before `datagram@3` became the default, a package that took the defaults ran
on `datagram@2`. Its first build after the change is a wire change, and its
next release a breaking one. Stating `wire = { framing = "datagram@2" }` keeps
the old wire. See [Defaults before `comline@2`](../handshakes/index.md#defaults-before-comline2).

Both framings carry frames in either direction, so either end can start a
call, and several protocols can share one connection. Every frame starts
with a kind byte: `0` for a request, `1` for a reply.

**Varints** are unsigned LEB128, as in [`packed@1`](../formats/packed@1.md): 7 bits per
byte, low bits first, high bit set on every byte but the last. A protocol
or function number is a `u16`, so it takes 1 to 3 bytes. Only the shortest
form is accepted: `80 00` for 0 is refused, and so is a value above 65535.

## The envelope

A reply's outcome, the same in both framings:

| Outcome | Bytes |
|   ---   |  ---  |
| ok      | `00`, then the result |
| error   | `01`, the error's ordinal (`u16` LE), then its body |
| fault   | `02`  |

## Proven by

The byte-exact vectors in the runtime's corpus:
`framing-datagram2` and `framing-datagram3`
([vectors](https://github.com/ComlineProject/runtime/tree/main/runtime/conformance/vectors)).
These include rejections: an unknown kind, overlong or out-of-range
numbers, a short request, and a reply read as a request.

