# `datagram@2`

| Frame | Bytes |
| --- | --- |
| request | `00`, protocol (varint), call id (`u16` LE), request id (`u64` LE), arguments |
| reply | `01`, protocol (varint), request id (`u64` LE), envelope |

- The **call id** is the function's position in its protocol, and the
  **protocol** number is the protocol's position in the package. Both ends
  share them because `comline@1` refuses a peer whose IR differs.
- Reordering or inserting functions therefore changes what a call
  addresses: the profile states `calls = by_index`.
