# Proposal D — a maximum only: `Order[max 100]`

Status: **leaning** · A string's maximum is `string(max n)` (decided
2026-11-02) · See the [section overview](index.md) for the question all four
answer

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

The array form is `T[max N]`. A **string's** own maximum can't be written
`string[max 64]`, because that's an array of up to 64 strings. It's written
**`string(max 64)`** (decided 2026-11-02). Two forms were weighed:

| | Chosen: `string(max 64)` | Not chosen: `string max 64` |
|---|---|---|
| A field | `name: string(max 32)` | `name: string max 32` |
| Inside a union | `union(string(max 16) u32)` | `union(string max 16 u32)`: harder to see where the member ends |
| An array of bounded strings | `string(max 32)[max 10]` | `(string max 32)[max 10]`: needs grouping |

`string max 64` reads well alone, but inside a union or an array it needs
grouping, so the parenthesized form won.

```ids
const MAX_NAME: u32 = 64

/// A display name: at most 32 characters.
type AccountName = string(max 32)

/// Raw image bytes, at most 64 KiB.
type Avatar = u8[max 65536]

struct Customer {
    id: u64
    /// Never empty: the minimum is a validator.
    @validators = [StringBounds(min_chars = 1)]
    name: AccountName
    optional email: string(max 254)
    /// Up to 10 tags of up to 32 characters each.
    tags: string(max 32)[max 10]
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
    discount: union(string(max 16) u32)
    optional note: string(max MAX_NAME)
}

struct OrderLine {
    /// Exactly 8 characters: the maximum in the type, the minimum a validator.
    @validators = [StringBounds(min_chars = 8)]
    sku: string(max 8)
    /// A month, 1 to 12: a value rule, so a validator, not a bound.
    @validators = [IntRange(min = 1, max = 12)]
    month: u8
}

/// Up to 16 rows, each with up to 8 labels of up to 20 characters.
struct Board {
    rows: string(max 20)[max 8][max 16]
}

error OutOfStock {
    message = f"{item} is out of stock"
    item: string(max 64)
}

protocol Orders {
    function place(order: Order) -> u64;
    function search(query: string(max 100), limit: u32) -> Order[max 50];
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
- **A string's maximum is written differently from an array's:**
  `string(max 64)` against `T[max 64]`, since `string[max 64]` is already an
  array of strings.
- **Exact strings** (`sku`, exactly 8 characters) take two pieces: the maximum in
  the type, the minimum in a validator.
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
bound is checked by every decoder. If "at least one item" must hold for every
receiver, D needs either validation on by default, or minimums lowered into the
decoder as in option 1.

## When this would be the right call

If bounds are there to protect decoders and nothing else, and readability
without explanation matters more than writing a minimum in the type.
