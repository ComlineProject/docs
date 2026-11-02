# Proposal C — bounds as annotations

Status: **under discussion** · See the [section overview](index.md) for the
question all three answer

**The idea:** the type's spelling doesn't change. A bound is an annotation on
the field or alias that holds the value: `@length` for a string's characters,
`@items` for an array's items. The bound still lives in the type in the IR,
just as it does under A and B.

## Shape

```ids
const MAX_NAME: u32 = 64

/// A display name: 1 to 32 characters.
@length = 1..32
type AccountName = string

/// Raw image bytes, at most 64 KiB. `T[a..b]` could stay for arrays;
/// shown here with `@items` to keep one form.
@items = ..65536
type Avatar = u8[]

/// A tag: up to 32 characters. A bounded element needs an alias.
@length = ..32
type Tag = string

@length = 4..16
type Coupon = string

struct Customer {
    id: u64
    name: AccountName
    @length = ..254
    optional email: string
    /// Up to 10 tags.
    @items = ..10
    tags: Tag[]
    optional avatar: Avatar
}

/// Exactly 3 floats: the fixed array, unchanged.
struct Point {
    pos: f32[3]
}

struct Order {
    customer: Customer
    @items = 1..100
    lines: OrderLine[]
    discount: union(Coupon u32)
    @length = ..MAX_NAME
    optional note: string
}

struct OrderLine {
    @length = 8..8
    sku: string
    quantity: u32
}

/// Up to 16 rows, each with 2 to 8 labels of up to 20 characters.
@length = ..20
type Label = string
@items = 2..8
type Row = Label[]
struct Board {
    @items = ..16
    rows: Row[]
}

error OutOfStock {
    message = f"{item} is out of stock"
    @length = ..64
    item: string
}

struct Signup {
    @length = ..32
    @validators = [StringBounds(min_chars = 3)]
    handle: string
}

@length = 1..100
type SearchQuery = string
@items = ..50
type Results = Order[]

protocol Orders {
    function place(order: Order) -> u64;
    function search(query: SearchQuery, limit: u32) -> Results;
    function rename(id: u64, name: AccountName) -> ();
}
```

## The case for it

- **Nothing looks like `string[]`.** The type stays `string`. The bound is
  named, `@length` or `@items`, so it says what it limits.
- **Each kind of limit has its own name.** If range bounds on scalars ever come,
  `@range = 1..12` doesn't look like a size bound
  ([Which types take a bound](index.md#which-types-take-a-bound)).
- **No new grammar:** annotations already exist, along with their hover,
  completion and formatting.
- **Settings can set a default,** like any annotation (a package-wide maximum
  string length, say).
- **Familiar from** Protobuf field options and JSON Schema's `maxLength` /
  `maxItems`.

## The case against

- **Nested bounds need aliases.** A bounded element in an array, or a bounded
  string inside a union, can't be written in place: `Tag`, `Label`, `Row` and
  `Coupon` above exist only to carry a bound.
- **Function parameters and returns** need aliases too, unless annotations on
  parameters are added to the grammar.
- **Further from the type:** the bound sits on a line above, not next to the
  type it limits. Moving a field means moving its annotation with it.
- **A bound that looks like a setting is part of the wire contract.** Its
  change is breaking, as under A and B, but annotations mostly don't change
  the wire, so this one is an exception to explain.

## When this would be the right call

If explaining a bracket after `string` is the larger cost, and bounds will
mostly sit on aliases and plain fields, not inside unions, nested arrays or
parameter lists.
