# Proposal D — a maximum only: `Order[max 100]`

Status: **leaning** · Strings are `char[]`, so a bounded string is
`char[max n]` ([decided 2026-11-02](char-strings.md), replacing `string(max n)`)
· Issues and resolutions [below](#issues-and-resolutions) · See the
[section overview](index.md) for the question all four answer

**The idea:** a type carries only a **maximum**, written with the word `max`:
`Order[max 100]` is at most 100 orders. There's no minimum and no range.
Minimums ("at least one", "not empty") stay with validators. `T[N]` stays
exactly `N`.

## Why only a maximum

- **The maximum is the whole reason for bounds.** It lets a decoder refuse a
  huge length before allocating. A minimum never prevents an allocation.
- **A minimum is a rule about the value,** like "not empty", and that's what
  validators are for.
- **One number can't be misread as a range.** `T[1..12]` can read as a slice
  (elements 1 to 12, as in Rust and Python), as numbering, or as a count over
  time. `T[max 12]` says what it means
  (see [Misreadings](index.md#misreadings-a-spelling-must-avoid)).
- **The word separates "at most" from "exactly":** `f32[3]` is exactly 3,
  `f32[max 3]` is up to 3. They don't differ only by which bracket is used.
- **It leaves nothing to say about integers.** `u8(1..12)` was ambiguous: a
  value from 1 to 12, a count like `u8[1..12]`, or a call. Under D, integers
  take no bound, and a value range is a validator.

## Shape

Every bound is `T[max N]`, strings included. A string is an array of `char`
([Strings as `char[]`](char-strings.md)), so a string of at most 64 characters
is `char[max 64]`, and exactly 2 characters is `char[2]`. `string` stays the
built-in name for `char[]`, and takes no bound itself.

*History:* a string's maximum was first decided as `string(max 64)`, a form
only strings had. Making strings `char[]` replaced it the same day, so one
syntax covers everything.

```ids
const MAX_NAME: u32 = 64

/// A display name: at most 32 characters.
type AccountName = char[max 32]

/// Raw image bytes, at most 64 KiB.
type Avatar = u8[max 65536]

struct Customer {
    id: u64
    /// Never empty: the minimum is a validator.
    @validators = [NonEmpty()]
    name: AccountName
    optional email: char[max 254]
    /// Up to 10 tags of up to 32 characters each.
    tags: char[max 32][max 10]
    optional avatar: Avatar
}

/// Exactly 3 floats: the fixed array, unchanged.
struct Point {
    pos: f32[3]
}

struct Order {
    customer: Customer
    /// At least one line (a validator), at most 100 (the type).
    @validators = [NonEmpty()]
    lines: OrderLine[max 100]
    discount: union(char[max 16] u32)
    optional note: char[max MAX_NAME]
}

struct OrderLine {
    /// Exactly 8 characters: an exact length is in the type.
    sku: char[8]
    /// A month, 1 to 12: a value rule, so a validator, not a bound.
    @validators = [IntRange(min = 1, max = 12)]
    month: u8
}

/// Up to 16 rows, each with up to 8 labels of up to 20 characters.
struct Board {
    rows: char[max 20][max 8][max 16]
}

error OutOfStock {
    message = f"{item} is out of stock"
    item: char[max 64]
}

protocol Orders {
    function place(order: Order) -> u64;
    function search(query: char[max 100], limit: u32) -> Order[max 50];
    function rename(id: u64, name: AccountName) -> ();
}
```

`NonEmpty` and `IntRange` aren't in std today. They're shown as the validators
this proposal would need.

## The case for it

- **Each spelling reads aloud as what it means:** "order, max 100". It can't be
  taken for a slice, numbering, a count over time, or a call.
- **"Exactly" and "at most" are distinct by a word,** not by a bracket.
- **Smallest concept:** one number, one meaning ("never more than"), and every
  bound protects a decoder.
- **Integers are settled:** no bound syntax, so no `u8(…)` question.
- **Changing a minimum isn't a wire change,** and as a validator it isn't
  reported as one.

## The case against

- **"At least one" moves to a validator.** It's common (non-empty names, lists
  with at least one item), and it needs validators std doesn't have yet:
  `NonEmpty` and `IntRange`.
- **A validator's minimum is checked after decoding, not during.** That's no
  loss for safety, since minimums don't protect allocation, but an empty list
  is refused one step later.
- **A new word, `max`,** inside type brackets.
- **`string[max 64]` is an array of strings,** while a bounded string is
  `char[max 64]`. Someone meaning the second may write the first
  ([Strings as `char[]`](char-strings.md#issues)).
- **A minimum as a validator costs more, and isn't always enforced.** See
  [What a validator minimum costs](#what-a-validator-minimum-costs).

## What a validator minimum costs

Under D, the maximum stays in the type and is checked while decoding. Only the
**minimum** moves to a validator. So the question is what checking a minimum
in a validator costs, compared with checking it during decoding.

**How validators run today** ([core#96](https://github.com/ComlineProject/core/issues/96)):

- **Rust:** generated types implement `Validate`. On receipt they run only when
  the receiver sets `validate_on_decode = "collect"` or `"first"`; the default
  is `off`. When on, a struct decodes into an unchecked shadow type first, and
  its checks run as a separate pass over the decoded value.
- **TypeScript:** validators aren't generated yet (core#96, step 4d).
- A bound, by contrast, would be enforced by **every** decoder, always.

**The cost of each minimum, per value:**

| Minimum | Checked during decoding (a bound) | Checked as a validator |
|---|---|---|
| Array, at least N items | one comparison against the count the decoder already read | one comparison against `len()`, after the whole array is decoded |
| String, at least N characters | one comparison: the decoder already counts characters to check the maximum | a **second pass** over the string to count its characters (`chars().count()` in Rust) |
| Rejecting a bad value | before decoding the rest of the message | after the whole message is decoded |

What that means:

- **Arrays:** the same cost either way, one comparison. The validator only
  runs later.
- **Strings:** the validator pays an extra pass over each string's bytes. It's
  linear in the string's length: negligible for a name, measurable for long
  text or many strings per message. A bound would reuse the count the maximum
  check already took.
- **Rejected values:** a validator spends work decoding the rest of a message it
  will refuse. That's the failure path, so it matters for abuse (a peer
  sending many invalid messages), not for normal traffic.
- **Per message:** validation on decode adds the shadow-type conversion and a
  walk over every field that has checks. In Rust the conversion moves fields
  and doesn't copy them, so its cost is that walk, proportional to the number
  of checks.
- **None of this is measured.** No benchmark covers validators yet. The
  runtime's instruction-count benchmarks could take a case per row above.

**Two ways to close the gap,** if it matters:

1. **Generators lower known validators into the decoder.** `StringBounds` and a
   std `NonEmpty` have fixed meanings, so a generator could check them during
   decoding, reusing the character count. The schema keeps D's spelling; the
   cost becomes a bound's.
2. **A minimum in the type after all,** as A to C allow, accepting the
   misreadings D avoids.

**The larger difference is enforcement, not speed.** A validator minimum is
checked only when the receiver opts in, and not at all in TypeScript today. A
bound is checked by every decoder. Decided since: validators are enforced by
default, and turning them off is an explicit give-up
([issue 8](#issues-and-resolutions)).

## Issues and resolutions

Raised 2026-11-02 while weighing D. **Decided** marks what the user settled;
**proposed** is a resolution not yet agreed.

| # | Issue | Resolution | State |
|---|---|---|---|
| 1 | `max` becoming a keyword would break names already in use: validator parameters called `max`, `params.max` | `max` is a keyword only right after `[` in a type; everywhere else it stays a name. Tests prove `max: u32` and `params.max` still parse | **decided** |
| 2 | A bound after an alias can't narrow it: with `type Tags = char[max 32][max 10]`, `Tags[max 5]` is an array of 5 `Tags` lists, not "Tags, at most 5" | No bound on a named type; a tighter limit is a new alias: `type FewTags = char[max 32][max 5]`. Narrowing would need its own syntax, since a suffix after a name already means an array; see [Narrowing an alias](#narrowing-an-alias) for what it would imply | open |
| 3 | Constants as bounds | Allowed: `char[max MAX_NAME]`, any unsigned integer constant, stored resolved. A dependency's constant changing changes your wire contract, and version comparison reports it | **decided** |
| 4 | `max 0`, values too large for a target, and messages too large for a framing or a connection | `max 0` is an error. Core caps at `u32::MAX`. **A target supports the full declared maximum or refuses to generate,** naming the target, so nothing quietly accepts less. Each message's worst-case size, per format, is checked against each framing's default frame limit and against every limit a consumer configures: the language server resolves them from the schemas, `config.idp` and the consumer's configuration. Generated code passes each protocol's worst-case size to its connection, and the shared runtime core refuses a connection configured below it unless that's given up explicitly | **decided** |
| 5 | Nested bounds read right to left: in `char[max 20][max 8][max 16]` the outermost limit comes last | Hover and diagnostics say it in words ("up to 16 rows, each up to 8 labels, each up to 20 characters"); a lint suggests an alias past two bounded levels. Prefix arrays, as Go writes them, were considered and not proposed: they'd change every array | proposed |
| 6 | A bounded array of unbounded values isn't bounded: ten strings of a gigabyte each fit `string[max 10]`; recursive types nest without limit | **No unbounded string or dynamic array, at any position:** reachability crosses packages, since a dependent's protocol can use your types. Each maximum comes from, in order: the position itself; a package default in settings ([core#125](https://github.com/ComlineProject/core/issues/125)), e.g. `defaults.max.string = 4096`, stored resolved at each position it reaches, so changing it is reported wherever it lands; or a give-up, [`@unverified = "reason"`](../guarantee-marker/index.md), making "bounded size" one of the guarantees core works out and consumers accept per protocol. **A type that can contain itself needs a depth limit** from the same three sources (`@max_depth = 32`, a settings default, or a give-up), enforced by decoders through the shared runtime core. Every message then has a computable worst-case size (issue 4). The build lists each unbounded position with a suggested fix; existing schemas break, which is acceptable before 1.0 | **decided** |
| 7 | `StringBounds` brings a hidden maximum: `max_chars` defaults to 1024, so `StringBounds(min_chars = 1)` on `char[max 2000]` refuses 1025 to 2000 characters after decoding | `StringBounds` stops carrying a maximum: `max_chars` defaults to `u32::MAX`, then is deprecated, since the type always has one (issue 6). std gains `NonEmpty` and `MinChars`. The build errors when a validator's minimum exceeds the type's maximum, and warns when a validator caps lower than the type | direction **decided**; details proposed |
| 8 | Validator minimums are enforced only when the receiver opts in, and not at all in TypeScript; and whether senders check | **Validators are enforced everywhere by default.** `validate_on_decode` defaults to checking; turning it off is an explicit give-up with a reason, recorded and visible like `@unverified`. This breaks Rust consumers relying on today's `off` default. TypeScript's support claim stays `partial` until it generates validators ([core#96](https://github.com/ComlineProject/core/issues/96), step 4d). **Senders likely check too,** on the value before encoding, so the check is the same in every format; what depends on the format and framing is examined in [Senders, by format and framing](#senders-by-format-and-framing) | enforcement **decided**; senders leaning, under examination |
| 9 | What a string's bound counts, and byte budgets | Strings are `char[]`, counted in characters: [Strings as `char[]`](char-strings.md). Byte budgets belong to the framing | **decided** |
| 10 | Adopting a maximum is breaking: adding one to an unbounded field tightens it, so a major version | Accepted before 1.0. Later, version comparison may weigh direction (via `@provider` from [packet dispatch](../packet-dispatch.md)), so a limit on a value only the server receives breaks nobody | **decided** |
| 11 | A generator using fixed-capacity types (`ArrayString<32>`) changes its consumers' code when a maximum changes, beyond the wire | Fixed-capacity types are opt-in in a generator's configuration; the default is the language's normal heap type with a check | to be proposed |
| 12 | Every language pays for checking, and writes the check itself | Following the [shared runtime core](../shared-runtime-core/index.md): the core owns what is bytes and integers, not host values. **Decoding** works on bytes, so "strict UTF-8 and count characters up to N" can be a core primitive; it moves into a language's path only where instruction counts show the call is at least as fast, as in [stage 4](../shared-runtime-core/index.md#stage-4-moving-typescript). **Encoding** starts from a host string, which the core doesn't own. The rule itself is written once: [stage 3](../shared-runtime-core/generated-codecs.md)'s layout plan carries each maximum, and every generator renders the check from it, held together by the vectors and differential fuzzing. The runtime cost per language is what the [validator benchmarks](../validator-benchmarks.md) would measure | proposed |
| 13 | Transports have limits of their own (a UDP datagram holds about 65 KB), which no configuration states today | Transports are declared in configuration, with their limits, and take part in the guarantees core works out: a protocol whose worst-case message exceeds its transport's limit is an error, or a give-up. How transports are declared is a design of its own | open: raised 2026-11-02 |

### Narrowing an alias

Issue 2 is open. What narrowing an alias (`AccountName`, but at most 16 here)
would imply:

- **It needs a new syntax.** A suffix after a name already means an array, so
  narrowing would be written some other way: `AccountName(max 16)`, which
  brings back the `(…)` form strings just left, or an annotation on the field,
  `@max = 16`.
- **The value is no longer exactly the alias.** A generated checked type for
  `AccountName` ([level 2](char-strings.md#generated-code)) guarantees "at most
  32"; it can't also guarantee "at most 16". The narrowed position becomes
  either an unnamed type, losing the name, or the alias plus one more check,
  where the type no longer states the whole limit.
- **Nested aliases need a path.** For `type Tags = char[max 32][max 10]`,
  narrowing has to say which level: the tags or each tag.
- **Docs and hover show two limits** for one position: the alias's and the
  narrowed one.

Without narrowing, a tighter limit is a new alias: an explicit name, its own
generated type, and nothing to resolve. The cost is more aliases.

### Senders, by format and framing

The sender checks the value before encoding, so the check itself is the same in
every format. What changes:

| Format | When the sender can refuse | Notes |
|---|---|---|
| `packed@1`, `msgpack@1` | before writing anything: lengths come before content | the fast path is free |
| `json@1` | before writing, from the in-memory value | no length is sent, but the check is the same |
| `msgpack@2` (planned, name-keyed structs) | as `msgpack@1` | |
| Third-party formats (`com.acme.cbor@1`) | in the format's own encoder | Comline can't prove it enforces bounds: that's encoding conformance, a guarantee `@unverified` already covers |

| Framing or transport | What it changes |
|---|---|
| `datagram@1`, `datagram@2`, `jsonrpc@1` | nothing for the check: the body is encoded whole, then framed |
| A stream transport (a `u32` length prefix) | the worst-case size against `max_frame` (issue 4) |
| Datagrams over UDP | a hard ceiling of about 65 KB per datagram (issue 13) |
| Packet framings (`comline.packet@1`, legacy ones, from [packet dispatch](../packet-dispatch.md)) | their maximum packet size, a framing parameter, checked like a frame limit; with compression, against the uncompressed size |
| Streams (an [open design](https://github.com/ComlineProject/docs/issues/98)) | a stream isn't one value, so bounds don't apply; "at most N items per stream" would be the stream's own limit, decided in that design |

How a refused value is reported depends on the framing:

| Refused | What happens |
|---|---|
| A request's parameters | the call fails locally; nothing is sent |
| A reply from a handler | the server can't send it; the caller gets an error instead: a `Fault` under `datagram@2`, an error object under `jsonrpc@1` |
| A one-way call | dropped, with an error to the local caller |

A framing that can't carry an error states, in its specification, how a refused
reply is handled.

## When this would be the right call

If bounds are there to protect decoders and nothing else, and readability
without explanation matters more than writing a minimum in the type.
