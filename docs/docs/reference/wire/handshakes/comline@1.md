# `comline@1`

Each end sends one fixed 31-byte frame and refuses unless the peer's
matches:

| Bytes | Field |
| --- | --- |
| 2 | magic, `"CO"` |
| 1 | version, `01` |
| 8 | the schema fingerprint (IR hash), `u64` LE |
| 8 | the format's name hash (FNV-1a 64), `u64` LE |
| 8 | the framing's name hash, `u64` LE |
| 4 | capability bits, `u32` LE (advisory) |

Any edit to the schema changes the fingerprint, so the two ends must have
been built from the same schema.

