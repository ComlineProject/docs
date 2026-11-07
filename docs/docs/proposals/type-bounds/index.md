# Bounds on types

> **Decided 2026-11-02: [Proposal D](max-only.md),** a maximum only, written
> `T[max N]` for everything, with strings as arrays of `char`
> ([Strings as `char[]`](char-strings.md)), so a bounded string is
> `char[max 64]` and a string bound counts characters. A, B and C are rejected:
> their ranges proved easy to misread
> (see [Misreadings](#misreadings-a-spelling-must-avoid)). The decided design
> and its rollout are in the [Design record](../../design/type-bounds.md);
> D's issues and resolutions are [on its page](max-only.md#issues-and-resolutions).

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

Four proposals answer the question, written to the same shape. Tracked in
[core#98](https://github.com/ComlineProject/core/issues/98).

| | Bounded string | In one line |
|---|---|---|
| [Proposal A](parentheses.md) | `string(1..32)` | the bound in parentheses after `string` |
| [Proposal B](angle-brackets.md) | `string<1..32>` | the bound in angle brackets after `string` |
| [Proposal C](annotation.md) | `@length = 1..32` on the field or alias | the bound as an annotation, not part of the type's spelling |
| [Proposal D](max-only.md) | `char[max 32]`, arrays `Order[max 100]` | a maximum only, written with `max`; strings are `char[]`; minimums stay with validators |

## The same schema, four ways

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

// D: maximums only; a minimum is a validator
type AccountName = char[max 32]
struct Customer {
    tags: char[max 32][max 10]
    discount: union(char[max 16] u32)
}
protocol Orders {
    function search(query: char[max 100], limit: u32) -> Order[max 50];
}
```

Each proposal page has the full example: aliases, nested arrays, fixed arrays,
unions, function parameters and returns, errors, and validators on top of a
bound.

## How they compare

| | A `string(..n)` | B `string<..n>` | C `@length` | D `[max n]` |
|---|---|---|---|---|
| Can be confused with `string[]` | yes: a bracket after `string`, like the array suffix | yes, as A | no: the type stays `string` | no `string(…)` form; but `string[max 64]` (strings) and `char[max 64]` (a string) differ |
| Can be read as a slice or numbering | yes: `T[1..12]` | yes | the range in `@items = 1..12` too | no: one number |
| "Exactly" against "at most" | `T[3]` against `T[..3]` | as A | `T[3]` against `@items = ..3` | `T[3]` against `T[max 3]` |
| A minimum in the type | yes | yes | yes | no: a validator |
| Inside a union or a parameter list | parentheses inside parentheses | reads as a type | needs an alias | `union(char[max 16] u32)` |
| A bounded element in a bounded array | `string(..32)[..10]` | `string<..32>[..10]` | an alias for the element | `char[max 32][max 10]` |
| Keeps `<>` free for generics | yes | no | yes | yes |
| New grammar | a suffix on `string` | a suffix on `string` | none: an annotation | `max` inside `[]`, and the `char` type |
| Settings can set a default bound | no | no | yes, like any annotation | no |
| Familiar from | SQL `varchar(64)` | Rust and TypeScript generics | Protobuf field options, JSON Schema `maxLength` | Protobuf validate's `max_len` |

## Shared, whichever is chosen

- **`T[N]` stays exactly `N`.** An array's maximum is `T[..10]` under A and B,
  `@items` under C, and `T[max 10]` under D.
- **Under A to C, ranges are inclusive at both ends.** `..64` means at most 64,
  the way `StringBounds(max_chars = 64)` reads. D has no ranges.
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

**Decided 2026-11-02: size bounds only, on strings and dynamic arrays** (rule 1
below); integer ranges stay with validators (`IntRange`). What follows is the
comparison that led there. core#98 names arrays and strings, and its reason,
refusing an oversized value before allocating, only covers types whose size
varies. A bound could mean two different things:

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

## Misreadings a spelling must avoid

Each of these came up when reading the examples above. A spelling that allows
one needs the docs, hover and diagnostics to undo it every time.

| Written | Meant | Can be read as |
|---|---|---|
| `Order[1..100]` | each value holds 1 to 100 orders | a **slice**, elements 1 to 100 of a list, as `xs[1..100]` is in Rust and Python |
| `Order[1..100]` | each value holds 1 to 100 orders | **numbering**: the items numbered 1 to 100 |
| `Order[1..100]` | each value holds 1 to 100 orders | **traffic**: someone may send 1 to 100 orders over time, or must send them all at once |
| `u8(1..12)` | a `u8` whose value is 1 to 12 | a **count**, since `u8[1..12]` right beside it is 1 to 12 `u8`s |
| `u8()`, `string()` | a type | a **call** or a **constant** |
| `string(..64)`, `string<..64>` | a string of at most 64 characters | something in the **family of `string[]`**, the array |

What a bound always means, whatever the spelling:

- **It describes one value.** Every value of that field, parameter or return is
  checked on its own, in the message that carries it.
- **It says nothing about traffic:** how many messages are sent, how often, or
  whether items arrive at once or over time. Nothing accumulates across
  messages.
- **"At most" is not "exactly".** `T[N]` is exactly `N` in every value.

## What a string bound counts

**Decided 2026-11-02: characters,** by making strings arrays of `char`
([Strings as `char[]`](char-strings.md)). What follows is the comparison that
led there.

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
- ~~**What a string bound counts**~~: decided, characters, with strings as
  `char[]` ([Strings as `char[]`](char-strings.md)).
- ~~**Constants as bounds**~~: decided, allowed
  ([issue 3](max-only.md#issues-and-resolutions)).
- **An exact length:** `8..8` only, or a shorthand. A shorthand like
  `string(8)` reads too much like the fixed array `f32[3]`.
- ~~**Which types take a bound**~~: decided, size bounds only: maximums on
  strings and dynamic arrays. See [Which types take a bound](#which-types-take-a-bound).
- **Under D, the cost of minimums as validators:** an extra pass per string,
  and checks that run only when the receiver opts in
  ([weighed here](max-only.md#what-a-validator-minimum-costs)). Unmeasured.
- ~~**Under D, a string's own maximum**~~: decided, `char[max 64]`, replacing
  the earlier `string(max 64)` ([why](char-strings.md)).
- ~~**Under D, minimum validators std would need**~~: shipped in std,
  `NonEmpty`, `MinChars`, `MinItems` and `IntRange`
  ([the guide](../../guides/idl/validator.md#the-standard-validators)).
