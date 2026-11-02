# Proposal B — `string<..n>`

Status: **rejected** 2026-11-02: the same misreadings as
[A](parentheses.md), and it takes `<>` from generics;
[Proposal D](max-only.md) was accepted · See the
[section overview](index.md) for the question all four answer

**The idea:** a string's bound follows it in angle brackets: `string<1..32>`.
Array bounds use the array suffix: `T[1..10]`.

## Shape

```ids
const MAX_NAME: u32 = 64

/// A display name: 1 to 32 characters.
type AccountName = string<1..32>

/// Raw image bytes, at most 64 KiB.
type Avatar = u8[..65536]

struct Customer {
    id: u64
    name: AccountName
    optional email: string<..254>
    /// Up to 10 tags of up to 32 characters each.
    tags: string<..32>[..10]
    optional avatar: Avatar
}

/// Exactly 3 floats: the fixed array, unchanged.
struct Point {
    pos: f32[3]
}

struct Order {
    customer: Customer
    lines: OrderLine[1..100]
    discount: union(string<4..16> u32)
    optional note: string<..MAX_NAME>
}

struct OrderLine {
    sku: string<8..8>
    quantity: u32
}

/// Up to 16 rows, each with 2 to 8 labels of up to 20 characters.
struct Board {
    rows: string<..20>[2..8][..16]
}

error OutOfStock {
    message = f"{item} is out of stock"
    item: string<..64>
}

struct Signup {
    @validators = [StringBounds(min_chars = 3)]
    handle: string<..32>
}

protocol Orders {
    function place(order: Order) -> u64;
    function search(query: string<1..100>, limit: u32) -> Order[..50];
    function rename(id: u64, name: AccountName) -> ();
}
```

Each suffix applies to what's on its left: `string<..20>[2..8][..16]` is up to
16 rows, each of 2 to 8 strings, each of up to 20 characters.

## The case for it

- **Reads as a type** inside unions and parameter lists:
  `union(string<4..16> u32)`, `search(query: string<1..100>, …)`.
- **Familiar from Rust and TypeScript,** where `<…>` qualifies a type.
- **No overlap with `()`,** the unit type.
- **Small grammar change:** an optional range after `string`. `<` and `>` are
  unused in the grammar today.

## The case against

- **Looks like `string[]`,** as Proposal A does: a bracket right after
  `string`, next to the array suffix. It needs the same explanation in the
  docs, hover and diagnostics.
- **Uses up `<>`.** If generics come (`Page<User>`), `string<..64>` and
  `Page<User>` share brackets with different meanings.
- **Range bounds on scalars** (`u8<1..12>`), if ever allowed, would look the
  same as a size bound but mean something else
  ([Which types take a bound](index.md#which-types-take-a-bound)).

## When this would be the right call

If generics are not expected, and readability inside unions and parameter lists
matters most.
