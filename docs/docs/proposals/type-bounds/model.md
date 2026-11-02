# How bounds work

Status: **under discussion** · Holds whichever [spelling](index.md) is chosen.
Examples use Proposal A's `string(1..32)` for brevity.

The [overview](index.md) compares how a bound is *written*. This page describes
what a bound *is*: which types take one, where it can be written, where it comes
from, and what each part of Comline does with it, from the schema to the bytes
on the wire.

## What a bound is

A bound limits one **measure** of a type, between an inclusive minimum and
maximum, for every value of that type:

```
min ≤ measure(value) ≤ max
```

A type takes a bound only if it has a measure. There are two kinds:

| Kind | The measure | Protects a decoder | Example |
|---|---|---|---|
| **Size** | how many things the value holds: characters, items | yes: a decoder can refuse an oversized value before allocating it | `string(1..32)`, `User[..100]` |
| **Range** | the value itself | no: a number takes the same space whatever its value | `u8(1..12)` |

A bound is **part of the type**, not a rule run afterwards.
- `string(1..32)` and `string` are different types. A value outside the bound
  isn't an invalid string: it isn't a value of that type at all, and is refused
  while decoding, like a malformed one.
- That's the line between a bound and a validator. A validator takes a
  well-formed value and judges it (an email address's shape, a field compared
  with another). A bound decides what the value can be at all.

## Which types take one

| Type | Measure | Bound | Why |
|---|---|---|---|
| `string` | characters (Unicode scalar values) | **yes**, size | the main case: protects decoders |
| `T[]` | items | **yes**, size | the main case |
| `T[N]` | items, fixed at `N` | **no** | already exact; a bound could only repeat `N` |
| A future bytes or map type | bytes, entries | **yes**, size | same reason as arrays |
| `u8`…`u64`, `s8`…`s64` | the value | **open:** range | see [Range bounds](#range-bounds-on-integers) |
| `f32`, `f64` | the value | **no** | see [Range bounds](#range-bounds-on-integers) |
| `bool` | | **no** | two values, nothing to limit |
| An enum | | **no** | its variants already are the set of values |
| A struct or error | | **no** | see [User types](#user-types) |
| A union | | **no**; its members can be bounded | see [Unions](#unions) |
| `()` | | **no** | |

Writing a bound on a type that doesn't take one is an error at build time:
`a bound doesn't apply to bool`.

### User types

A struct, error, enum or union **declaration** has no measure of its own, so
it takes no bound.
- **Its size depends on the format:** a `packed@1` struct and the same struct
  in `json@1` differ by an order of magnitude, so "at most 200 bytes" would
  mean different things on different wires.
- **It is already bounded through its fields.** A struct whose fields are all
  bounded is bounded as a whole, and a decoder refuses it field by field.
- **A limit on a whole message's encoded size is a framing concern:** a
  frame or packet limit, which every message under that framing gets.

Collections *of* user types are bounded as usual. `User[..100]` is at most 100
users. An alias to a user type (`type Admin = User`) takes no bound either,
because what it names has no measure.

### Range bounds on integers

Not decided: the [overview](index.md#which-types-take-a-bound) gives three
rules (size only; size and range; size now, range later). If ranges come, they
work like this:

- **The range must fit the type.** `u8(1..300)` is an error: 300 isn't a `u8`.
- **The declared type stays the generated type.** `u8(1..12)` is a `u8` in
  every language. The bound adds a check, not a narrower type.
- **The wire doesn't change.** Fixed-width formats send the full width.
  Variable-width formats already size by value. A decoder refuses an
  out-of-range value the way it refuses an integer too wide for its type today.
- **It doesn't protect a decoder,** which is the case against it. Every
  integer takes the same space, so a range bound is a value rule written into
  the type, overlapping validators.

**Floats are left out** either way:
- NaN is outside every range and equals nothing.
- `-0.0` against a minimum of `0.0` needs a ruling.
- Inclusive ends behave differently in each language once a decimal is parsed
  into a float.

A float rule belongs in a validator.

## Where a bound can be written

A bound sits on a **position** where a type is written, not on a declaration.
The same type can be bounded in one place and not in another.

| Position | Example |
|---|---|
| A field | `name: string(1..32)` |
| An `optional` field | `optional email: string(..254)` |
| An alias's target | `type AccountName = string(1..32)` |
| An array's element | `tags: string(..32)[..10]` |
| A nested array, each level | `rows: string(..20)[2..8][..16]` |
| A union member | `discount: union(string(4..16) u32)` |
| A function parameter | `function search(query: string(1..100))` |
| A function return | `function recent() -> Order[..50]` |
| A constant's type | `const CODE: string(4..4) = "AB12"` |

In a compound type, each bound applies to the part on its left:
`string(..32)[..10]` bounds each string to 32 characters and the array to 10
items.

### Optional

A bound applies to the value when it's present. `optional string(1..32)` is
either absent or a string of 1 to 32 characters, so absence isn't "zero
characters". A field that may be empty is written `string(..32)` (minimum 0),
and one that may be missing is written `optional`.

### Unions

Each member keeps its own bound, and the union adds none. A decoder first
decides which member arrived, then checks that member's bound.

In an untagged JSON union, `union(string(..32) u32)` given a 40-character
string has no member it fits, and is refused, the same as a JSON `true` would
be.

## Where a bound comes from

### Written, or through an alias

Today a bound comes from one of two places:

1. **Written at the position:** `name: string(1..32)`.
2. **Through an alias:** `name: AccountName`, where
   `type AccountName = string(1..32)`.

Aliases in Comline are transparent: `AccountName` *is* `string(1..32)`. But the
alias's name survives into the compiled schema and into code generation, so a
generator can still emit a named type for it. That's where a fixed-capacity
string would come from, if a generator chooses one.

**Bounding an alias again** (`name: AccountName(..16)`) is open:

| | Allowed? | Meaning |
|---|---|---|
| Narrowing (`..16` within `1..32`) | open | the intersection, `1..16`; the alias's promise still holds |
| Widening (`..64` against `..32`) | **no**, an error | it would break the alias's own promise |
| Not at all | open | write a second alias instead |

### Constants

A bound may name a constant (`string(..MAX_NAME)`), if that's allowed (open).
The compiled schema stores the resolved number, not the name. Changing the
constant changes every bound that uses it, and version comparison reports each
change.

### Defaults

**There's no hidden default.** `string` with nothing written stays unbounded,
as it is today, and the framing's frame or packet limit is the only backstop.

A package-wide default ("every string at most 4096 characters unless stated")
could later come from settings blocks supplying defaults
([core#125](https://github.com/ComlineProject/core/issues/125)). If so:

- the resolved bound is stored per position, so a generator and the
  comparison never consult settings;
- changing the default is a breaking change, reported at every position it
  reaches.

### What's stored

The compiled schema records each position's bound **resolved**: aliases and
constants looked up, with any default applied. Everything downstream reads one
number pair per position. An unbounded type is stored exactly as today, so
existing builds keep their hashes.

## What each part does with it

### Build (core)

Refused at build time:
- a minimum above the maximum;
- a bound on a type that takes none, or a range outside the type
  (`u8(1..300)`);
- a bound on a fixed array `T[N]`;
- a value that breaks a bound: a field default, a constant's value;
- a bound and a validator no value can satisfy together, such as
  `string(..10)` with `StringBounds(min_chars = 20)`.

A warning when a validator only repeats a bound
(`StringBounds(max_chars = 64)` on `string(..64)`).

### Version comparison

**Any change to a bound is breaking.**
- **Tightening** breaks old senders, whose valid values the new reader refuses.
- **Loosening** breaks old receivers, which refuse the new writer's values.
- Adding a bound to an unbounded type is tightening; removing one is
  loosening.

A finer rule could weigh the direction a value travels: loosening a parameter
only the server receives breaks nobody. That's open, and would ride on
`@provider` from [packet dispatch](../packet-dispatch.md).

### Generated code

- **Sending:** the generated encoder refuses an out-of-bound value with a local
  error, before anything is sent. The mistake shows up at its source, not as
  a refusal on the other side.
- **Receiving:** the decoder refuses it as a decode error, in the same family
  as malformed input, and names the bound.
- **Types:** a generator may represent a bounded type more tightly: a
  fixed-capacity string, an array with inline storage. That's the generator's
  choice. The schema states the limit, not the representation.

### On the wire

The bytes don't change. Only what a decoder accepts does.

| Format | Array of at most N items | String of at most N characters |
|---|---|---|
| `packed@1`, `msgpack@1` | refuse a count prefix above N before allocating | refuse a byte-length prefix above 4 × N before allocating, then count characters exactly during the UTF-8 check decoders already run |
| `json@1` | stop at item N + 1 while parsing | count after unescaping; the frame limit caps the allocation |

Minimums are checked once the value is read.

### Validators

Bounds are checked first, while decoding. Validators run afterwards, on a value
already within its bounds.

### Documentation and the language server

- **Hover:** shows the bound in words, "string, 1 to 32 characters", and says
  it's checked while decoding.
- **Docs:** the doc model carries each position's bound, so generated docs show
  it next to the type.
- **Diagnostics:** name the bound in the same words as hover.

This explaining is what keeps a bracket after `string` from being read as the
array suffix, under whichever spelling is chosen.

## Open

- Whether integers take range bounds, and on what rule.
- Whether an alias's bound may be narrowed where it's used.
- Whether bounds may name constants.
- Whether a package-wide default comes, through settings.
- Whether comparison weighs direction, so loosening something only received
  is not breaking.
- What a string bound counts: characters, as on this page, or bytes
  ([the comparison](index.md#what-a-string-bound-counts)).
