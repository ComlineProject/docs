# Bounds on types

> **Under discussion.** No proposal is leading. How a bounded string is written
> is contested (see [Open points](#open-points)), and so is what a string bound
> counts.

**The question.** How does a schema say "at most 64 characters" or "1 to 100
items" as part of a type, so that a decoder can refuse an oversized value
**before allocating it**? A validator can't do that, because it only runs once
the value is fully decoded.

Where things stand:

- **Arrays** are `T[]` (any length) or `T[N]` (exactly `N`). Nothing in
  between.
- **Strings** have no bound at all. The `StringBounds` validator checks one
  after decoding.
- `string[]` already means *an array of strings*, so a string's own bound
  can't be written as `string[..64]`: that's an array of up to 64 strings.
- Settling this syntax is on the [1.0 list](../../conduct/readiness.md#schema-language).

What a bound is and how it works, whichever spelling is chosen, is in [How bounds work](model.md).

Three proposals answer the question, written to the same shape. Tracked in
[core#98](https://github.com/ComlineProject/core/issues/98).

| | Bounded string | In one line |
|---|---|---|
| [Proposal A](parentheses.md) | `string(1..32)` | the bound in parentheses after `string` |
| [Proposal B](angle-brackets.md) | `string<1..32>` | the bound in angle brackets after `string` |
| [Proposal C](annotation.md) | `@length = 1..32` on the field or alias | the bound as an annotation, not part of the type's spelling |

## The same schema, three ways

```ids
// A
type AccountName = string(1..32)
struct Customer {
    tags: string(..32)[..10]
    discount: union(string(4..16) u32)
}
protocol Orders {
    function search(query: string(1..100), limit: u32) -> Order[..50];
}

// B
type AccountName = string<1..32>
struct Customer {
    tags: string<..32>[..10]
    discount: union(string<4..16> u32)
}
protocol Orders {
    function search(query: string<1..100>, limit: u32) -> Order[..50];
}

// C
@length = 1..32
type AccountName = string
@length = ..32
type Tag = string               // a bounded element needs an alias
@length = 4..16
type Coupon = string            // likewise inside a union
@length = 1..100
type SearchQuery = string       // and as a parameter
@items = ..50
type Results = Order[]
struct Customer {
    @items = ..10
    tags: Tag[]
    discount: union(Coupon u32)
}
protocol Orders {
    function search(query: SearchQuery, limit: u32) -> Results;
}
```

Each proposal page has the full example: aliases, nested arrays, fixed arrays,
unions, function parameters and returns, errors, and validators on top of a
bound.

## How they compare

| | A `string(..n)` | B `string<..n>` | C `@length` |
|---|---|---|---|
| Can be confused with `string[]` | yes: a bracket after `string`, like the array suffix | yes, as A | no: the type stays `string` |
| Inside a union or a parameter list | parentheses inside parentheses | reads as a type | needs an alias |
| A bounded element in a bounded array | `string(..32)[..10]` | `string<..32>[..10]` | an alias for the element |
| Keeps `<>` free for generics | yes | no | yes |
| New grammar | a suffix on `string` | a suffix on `string` | none: an annotation |
| Settings can set a default bound | no | no | yes, like any annotation |
| Familiar from | SQL `varchar(64)` | Rust and TypeScript generics | Protobuf field options, JSON Schema `maxLength` |

## Shared, whichever is chosen

- **Array bounds are `T[a..b]`:** `T[1..10]`, `T[..10]` (at most 10),
  `T[2..]` (at least 2). `T[N]` stays exactly `N`. (Under C, `@items` sets the
  bound of a `T[]` field instead.)
- **Ranges are inclusive at both ends.** `..64` means at most 64, the way
  `StringBounds(max_chars = 64)` reads.
- **A bound is part of the type's shape,** so it lives in the frozen IR.
  Unbounded types stay byte-identical in the IR, so existing builds keep their
  hashes.
- **Aliases carry their bound.** `type AccountName = <bounded string>`, and
  validators on a field of that type add rules on top.
- **Contradictions are refused at build:** a minimum above the maximum, or a
  bound no value can meet together with a validator (at most 10 characters and
  `StringBounds(min_chars = 20)`).
- **Version comparison:** any change to a bound is breaking. Tightening breaks
  old senders, loosening breaks old receivers.
- **Generators decide the representation.** A bounded string *may* become a
  fixed-capacity, non-heap string. That's the generator's choice, not a schema
  or `comline.toml` setting.

## Which types take a bound

[How bounds work](model.md) has the full model: each type and why, every position a bound can be written in, where a bound comes from (written, through an alias, a constant, a default), and what the build, version comparison, generated code, decoders and the language server each do with it. This section is the short version.

Not settled. core#98 names arrays and strings, and its reason, refusing an
oversized value before allocating, only covers types whose size varies. A
bound could mean two different things:

- **A size bound:** how big a value may be (characters, items). It protects
  decoders and can change the generated type (a fixed-capacity string).
- **A range bound:** which values are allowed (a `u8` from 1 to 12). It
  protects nothing at decode time. It's a rule about the value, which is what
  validators are for today.

| Type | What a bound would limit | Kind | Case for | Case against |
|---|---|---|---|---|
| `T[]` | items | size | decoder safety; core#98's main reason | |
| `string` | characters | size | decoder safety | the unit question below |
| A bytes or map type, if added | bytes, entries | size | decoder safety | doesn't exist yet |
| Integers `u8`…`u64`, `s8`…`s64` | value | range | `month: u8(1..12)` is concise; a generator could pick a narrower type, and a packed format could encode fewer bits | it's what validators do; two ways to say one thing; no allocation to protect |
| `f32`, `f64` | value | range | as integers | NaN and infinity sit outside every range; inclusive ends on floats are awkward |
| `bool`, enums | nothing | | | nothing to bound |
| Structs, unions, `()` | nothing obvious | | an encoded-size limit for datagrams | belongs to the framing, not the type |
| `optional T` | `T`'s bound, when present | | | |
| An alias | its target's bound | | carries the bound where the alias is used | may a use tighten it again? |

Three possible rules:

1. **Size only:** types whose size varies (strings, arrays, and later bytes
   and maps). One meaning, "how big", and every bound protects a decoder.
   Value rules stay with validators.
2. **Size and range:** any scalar too, with one syntax for two meanings. More
   concise, but a bound no longer always protects a decoder, and it overlaps
   validators.
3. **Size now, range later:** ship rule 1, and keep the syntax able to take
   range bounds on scalars later without changing meaning.

The rule interacts with the syntax. Under A or B, `u8(1..12)` or `u8<1..12>`
would look the same as a string bound but mean a different kind of limit.
Under C, separate annotations (`@length`, `@items`, `@range`) keep each kind
apart.

## What a string bound counts

The issue first proposed UTF-8 **bytes**. Checking what strings are across the
project points to **characters (Unicode scalar values)** instead.

**Strings are characters everywhere already.** Every format and both
generators treat a string as a sequence of Unicode scalar values. Invalid UTF-8
and lone surrogates are refused, and `StringBounds` counts characters.

**On the wire:**

| Format | What's sent | Bytes per character |
|---|---|---|
| `packed@1`, `msgpack@1` | the UTF-8 byte length, then the text | 1–4 |
| `json@1` | escaped text, no length | 1–12 (`😀` is 12 bytes for one emoji) |

**In each language, a string's own "length" is:**

| Unit | Languages |
|---|---|
| UTF-8 bytes | Rust, Go |
| UTF-16 code units | JavaScript/TypeScript, Java, C#, Dart |
| characters | Python |
| grapheme clusters (by default) | Swift |

No single unit matches the wire, the formats and the languages at once, so the
bound is defined on the **value**, and each format derives its own early check:

| | Characters | UTF-8 bytes |
|---|---|---|
| Same meaning in every format and language | yes | no: exact only for UTF-8 formats and UTF-8 languages |
| Agrees with `StringBounds` | yes | no: two units for one idea |
| Refuse before allocating, `packed@1` / `msgpack@1` | yes: a length prefix over 4 × N | yes: a prefix over N |
| Exact check while decoding | free, during the strict UTF-8 check decoders already run | free |
| `json@1` | after unescaping; the frame limit caps allocation | the same |
| Cheap for a sender in a UTF-16 language | yes: counted from UTF-16 | needs an encoding pass |
| Fixes the encoded size | no: up to 4 × N bytes | yes, for UTF-8 formats |

UTF-16 units and grapheme clusters are not candidates: they depend on the
language or on the Unicode version.

If an exact byte budget is ever needed (a datagram's size, say), it belongs to
the format or framing as a frame or packet limit, not to the string's type.

A `char` type (one Unicode scalar value) is a separate question. It can't stand
in for bounded strings: `char[..64]` would travel as an array of 64 values,
encoded differently from `string`.

## Open points

- **Does a bracket after `string` read as "a different kind of string" or as
  "a collection of strings"?** `string()` and `string<>` sit right next to
  `string[]`, which is an array. Unless the documentation, the language server
  (hover, completion, diagnostics) and error messages all explain bounds well,
  `string(..64)` can look like it's in the same family as `string[]`. This
  argues for C, for a spelling with a keyword, or for teaching bounds as one
  concept across strings and arrays.
- **What a string bound counts:** characters, as argued above, or bytes, as
  first proposed.
- **Constants as bounds:** may a bound name a constant (`..MAX_NAME`), or
  only a literal?
- **An exact length:** `8..8` only, or a shorthand. A shorthand like
  `string(8)` reads too much like the fixed array `f32[3]`.
- **Which types take a bound:** size bounds only (strings, arrays), or range
  bounds on scalars too. See [Which types take a bound](#which-types-take-a-bound).
