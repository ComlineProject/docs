# Proposal D — a maximum only: `Order[max 100]`

Status: **under discussion** · See the [section overview](index.md) for the
question all four answer

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
`string[max 64]`, because that's an array of up to 64 strings. Its form is
open, between two candidates:

| | Variant D1: `string(max 64)` | Variant D2: `string max 64` |
|---|---|---|
| A field | `name: string(max 32)` | `name: string max 32` |
| Inside a union | `union(string(max 16) u32)` | `union(string max 16 u32)`: harder to see where the member ends |
| An array of bounded strings | `string(max 32)[max 10]` | `(string max 32)[max 10]`: needs grouping |

The example below uses D1.

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
- **The string form is still open,** with its own trade-offs (above).
- **Exact strings** (`sku`, exactly 8 characters) take two pieces: the maximum in
  the type, the minimum in a validator.

## When this would be the right call

If bounds are there to protect decoders and nothing else, and readability
without explanation matters more than writing a minimum in the type.
