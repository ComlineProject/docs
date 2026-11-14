# `datagram@3`

| Frame    | Bytes                                                                                      |
|  ---     |  ---                                                                                       |
| request  | `00`, protocol number (varint), function number (varint), request id (`u64` LE), arguments |
| reply    | `01`, protocol number (varint), request id (`u64` LE), envelope (as `datagram@2`)          |

- The numbers are the **wire numbers** core gives each protocol and
  function (core#127): unique in their scope, binding from `comline
  release`, and never reused once retired. Reordering or inserting
  functions doesn't move them, so the profile states `calls = by_id`.
- A reply is byte for byte a `datagram@2` reply.
- It's meant for [`comline@2`](../handshakes/comline@2.md), which checks
  compatibility by those same numbers.

For example, a call to function 3 of protocol 0, request id 42, with the
JSON arguments `[7,"x"]`:

```text
00 00 03 2a00000000000000 5b372c2278225d
```

Function 300 of protocol 300 is `00 ac02 ac02 …`, and 65535 is `ff ff 03`.
