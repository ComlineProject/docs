# Proposal A — `string(..n)`

Status: **under discussion** · See the [section overview](index.md) for the
question all four answer

**The idea:** a string's bound follows it in parentheses: `string(1..32)`.
Array bounds use the array suffix: `T[1..10]`.

## Shape

```ids
const MAX_NAME: u32 = 64

/// A display name: 1 to 32 characters.
type AccountName = string(1..32)

/// Raw image bytes, at most 64 KiB.
type Avatar = u8[..65536]

struct Customer {
    id: u64
    name: AccountName
    optional email: string(..254)
    /// Up to 10 tags of up to 32 characters each.
    tags: string(..32)[..10]
    optional avatar: Avatar
}

/// Exactly 3 floats: the fixed array, unchanged.
struct Point {
    pos: f32[3]
}

struct Order {
    customer: Customer
    lines: OrderLine[1..100]
    discount: union(string(4..16) u32)
    optional note: string(..MAX_NAME)
}

struct OrderLine {
    sku: string(8..8)
    quantity: u32
}

/// Up to 16 rows, each with 2 to 8 labels of up to 20 characters.
struct Board {
    rows: string(..20)[2..8][..16]
}

error OutOfStock {
    message = f"{item} is out of stock"
    item: string(..64)
}

struct Signup {
    @validators = [StringBounds(min_chars = 3)]
    handle: string(..32)
}

protocol Orders {
    function place(order: Order) -> u64;
    function search(query: string(1..100), limit: u32) -> Order[..50];
    function rename(id: u64, name: AccountName) -> ();
}
```

Each suffix applies to what's on its left: `string(..20)[2..8][..16]` is up to
16 rows, each of 2 to 8 strings, each of up to 20 characters.

## The case for it

- **Familiar from SQL:** `varchar(64)`.
- **Keeps `<>` free** for generics, should they come.
- **Small grammar change:** an optional range after `string`.
- **Reads as a parameter of the type:** "a string of 1 to 32".

## The case against

- **Looks like `string[]`.** A bracket right after `string` reads as if it
  belongs to the same family as the array suffix. Without good explanation in
  the docs, hover and diagnostics, `string(..64)` and `string[..64]` are easy
  to mix up, and they mean different things.
- **Parentheses inside parentheses** in unions and parameter lists:
  `union(string(4..16) u32)`, `search(query: string(1..100), …)`.
- **Looks like a call,** and `()` is already the unit type.
- **Range bounds on scalars** (`u8(1..12)`), if ever allowed, would look the
  same as a size bound but mean something else
  ([Which types take a bound](index.md#which-types-take-a-bound)).

## When this would be the right call

If keeping `<>` free matters most, and bounds are taught as one concept for
strings and arrays, so that `(…)` and `[…]` read as "the string's bound" and
"the array's bound".
