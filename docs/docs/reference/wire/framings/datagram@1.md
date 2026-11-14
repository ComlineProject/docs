# `datagram@1`

The first, lockstep datagram framing, also spelled `datagram`. A client sends
a request and reads its reply before sending the next, so frames carry no
kind byte and only the client starts a call.

| Frame | Bytes |
| --- | --- |
| request | call id (`u16` LE), request id (`u64` LE), arguments |
| reply | request id (`u64` LE), [envelope](index.md#the-envelope) |

- The **call id** is the function's position in its protocol. Both ends
  share it because `comline@1` refuses a peer whose IR differs, so the
  profile states `calls = by_index`.
- With no kind byte and no protocol number, a connection carries one
  protocol, called in one direction. [`datagram@2`](datagram@2.md) adds both.

For example, a call to function 3, request id 42, with the JSON arguments
`[7,"x"]`, and an ok reply to request 7:

```text
0300 2a00000000000000 5b372c2278225d
0700000000000000 00 7b22626f6479223a226869227d
```

Proven by the `framing-datagram` vectors in the runtime's
[corpus](https://github.com/ComlineProject/runtime/tree/main/runtime/conformance/spec/vectors).
