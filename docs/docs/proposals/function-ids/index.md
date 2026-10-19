# Function ids

> **Decided: [Proposal A](annotation.md), `@id = 0x2A`,** tracked in
> [core#127](https://github.com/ComlineProject/core/issues/127). The radix is
> left to the formatter and a lint; ids can be assigned on build and written
> into the source; reusing a retired id is an error. The default for
> assignment is derived from the framings (packet: `require`; JSON-RPC: `off`;
> datagram: `off` in `0.x`, then `write` from 1.0), and ids are all or none per
> protocol. See
> [its page](annotation.md#as-accepted).

**The question.** [Packet dispatch](../packet-dispatch.md#explicit-ids-available-everywhere)
lets any function state an explicit, fixed id, and requires one under a packet
framing. **How is the id written?**

These rules hold whichever syntax is chosen:
- the id is an integer, written in decimal (`42`) or hex (`0x2A`);
- it's unique within its family and direction;
- it's optional, except under a packet framing;
- in the version comparison, changing an id is major.

Hex needs a small grammar addition either way, since integer literals are
decimal-only today. Two proposals answer the question, written to the same
shape. Tracked in [core#123](https://github.com/ComlineProject/core/issues/123).

| | Syntax | In one line |
|---|---|---|
| [Proposal A](annotation.md) | `@id = 0x2A` | an annotation, like the other per-function settings |
| [Proposal B](prefix.md) | `0x2A# function login(…)` | a prefix on the declaration, from the 2024 proposal |

## How they compare

| | A `@id` | B prefix |
|---|---|---|
| Works with today's machinery | yes: an integer annotation, type-checked like `@timeout_ms` | no: new grammar on function declarations |
| Reads like a packet table | no: the id sits above the function | yes: ids line up down the left edge |
| Signals that the id is identity, not a setting | weak: it looks like any other annotation | strong: it's part of the declaration |
| Same form for family ids on protocols | yes: `@id` on a protocol too | needs the prefix on protocols as well |
| Gated or restricted through `settings` like other annotations | yes | only with a special case |
| Discoverability for newcomers | familiar annotation form | unusual; needs explaining |
