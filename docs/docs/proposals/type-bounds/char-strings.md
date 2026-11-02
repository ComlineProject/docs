# Strings as `char[]`

Status: **decided 2026-11-02: C2,** `string` is `char[]` · Part of
[Proposal D](max-only.md) · Replaces the earlier decision to write a string's
maximum as `string(max n)`

**The question:** what does a string's bound count, and how is a bounded
string written?

Three problems led here:
- **Languages disagree on a string's length:** UTF-8 bytes in Rust and Go,
  UTF-16 units in JavaScript, Java, C# and Dart, characters in Python, grapheme
  clusters in Swift ([the comparison](index.md#what-a-string-bound-counts)).
- **`string(max 64)` is a form only strings have.** It sits next to
  `string[]`, an array, and reads as if it belonged with it
  ([misreadings](index.md#misreadings-a-spelling-must-avoid)).
- **Byte budgets:** a string of at most 64 characters can take up to 256
  bytes.

## The options

| | Spelling | In one line | Assessment |
|---|---|---|---|
| **C1** | `string(max 64)`, plus `char` for one character | `char` exists, and a string's bound counts `char`s by definition | rejected: keeps the `string(…)` form and its misreading |
| **C2** | `char[max 64]`, `char[2]` | a string *is* an array of `char`, always sent as text; `string` is the built-in name for `char[]` | **decided** |
| **C3** | `string(max 64 chars)`, `string(max 256 bytes)` | the unit is written in the bound | rejected: a byte count is expensive in UTF-16 languages and means something else in JSON, which escapes text |

## C2: `string` is `char[]`

- **`char` is one Unicode scalar value:** a code point from U+0000 to U+10FFFF,
  excluding the surrogate halves. It's what every format and generator already
  treats a string as a sequence of: strict UTF-8, lone surrogates refused.
- **`char[]` is a string,** and `string` is the built-in name for it: a
  sequence of characters. `string` stays (decided 2026-11-02); existing
  schemas keep writing it.
- **Bounds use the array syntax, the same as every other array:**

  | Written | Means |
  |---|---|
  | `char[max 64]` | a string of at most 64 characters |
  | `char[2]` | a string of exactly 2 characters, such as a country code |
  | `string[max 10]` | an array of at most 10 strings |
  | `char[max 32][max 10]` | an array of at most 10 strings, each of at most 32 characters |

- **An array of `char` is always sent as text,** in every format, never as a
  list of separate values:

  | Format | `char[]`, `char[max N]`, `char[N]` |
  |---|---|
  | `packed@1`, `msgpack@1` | UTF-8 bytes after a byte-length prefix, as `string` is today |
  | `json@1` | a JSON string |

  So `char[max 64]` sends the same bytes as `string` does today. Adding a bound
  changes what a decoder accepts, not what's sent.
- **The measure is characters.** It agrees with `value.length` in validators,
  which already counts Unicode scalar values (core#109).
- **Decoders check it** as [How bounds work](model.md#on-the-wire) describes:
  - in `packed@1` and `msgpack@1`, a byte-length prefix above 4 × N is refused
    before allocating, then characters are counted exactly during the strict
    UTF-8 check decoders already run;
  - in `json@1`, characters are counted after unescaping.
- **`char[N]` is N characters, not N bytes.** Its encoded size still varies,
  1 to 4 bytes per character, so it isn't a fixed-size type the way `u8[N]` is.
- **Binary data is `u8[max N]`,** measured in bytes. A **byte budget** for a
  whole message (a datagram's size, say) belongs to the framing's frame or
  packet limit. Hover shows a string's worst case in bytes, 4 × N plus its
  length prefix, so the cost is visible.
- **Generated types:** see [Generated code](#generated-code).

## Generated code

Accepted 2026-11-02 on one condition: **no correctness or performance cost.**
Each level below states why it has none, and the
[validator benchmarks](../validator-benchmarks.md) are where that's measured
before it ships.

### Checking a maximum costs nothing in the common case

Every character takes at least one byte of UTF-8 and at least one UTF-16 unit.
So a string's character count is never more than its length in either:

- **Decoding:** if the byte-length prefix is at most N, the string has at most
  N characters, and nothing is counted. Above 4 × N it's refused before
  allocating. Only between N and 4 × N bytes are characters counted, during
  the strict UTF-8 check the decoder already runs.
- **Encoding:** in Rust, `len()` (bytes) at most N passes without counting. In
  TypeScript, `.length` (UTF-16 units) at most N passes the same way. Only a
  longer string is counted.
- **Exactly N (`char[N]`):** a byte length below N fails at once, and above
  4 × N likewise. Otherwise the UTF-8 check that already runs gives the count.

So counting happens only for a string near its limit, written in characters of
more than one byte. That's the cost any character-counted bound has, and it's
no more than the validator `StringBounds` already pays.

### Three levels

| Level | When | What `char[N]` and `char[max N]` become | Correctness | Performance |
|---|---|---|---|---|
| **1. Native string, checked** | always | the language's string: `String` or `&'a str` in Rust, `string` in TypeScript, `str` in Python, `string` in Go, `String` in Java, Kotlin, C# and Dart | the encoder and decoder check every value | the check above: free unless near the limit |
| **2. A checked type per named alias** | every named alias, such as `type CountryCode = char[2]` | Rust: a newtype, `pub struct CountryCode(String)`, `#[repr(transparent)]`, with `TryFrom<String>` and `Deref<Target = str>` but no mutable access. TypeScript: a branded string, `string & { readonly __brand: "CountryCode" }`, made with `CountryCode.from(s)`. Others: a value class or wrapper with a checked factory | a value of the type can't be built with the wrong length; nothing can change its length afterwards | none: the wrapper has the string's own layout. In Rust the encoder can skip the check, since the type already holds it. TypeScript's brand is only a type, so its encoder still checks, at the same cost as level 1 |
| **3. Fixed capacity** | only when the consumer's generator configuration opts in ([issue 11](max-only.md#issues-and-resolutions)) | Rust: an inline UTF-8 buffer of 4 × N bytes (`ArrayString`-like); C, through the C ABI: a buffer of 4 × N + 1 bytes | the same checks | no heap allocation, at the price of 4 × N bytes held inline even for short strings. A trade the consumer chooses, so not a cost imposed on anyone |

A bound written inline, not through an alias (`sku: char[8]`), is level 1 in
every language. In Rust it may instead use runtime-provided wrappers,
`CharsExact<N>` and `CharsMax<N>`, with level 2's layout and guarantees.

### A single `char`

Several languages call a UTF-16 unit a `char`, and it can't hold every
character (`😀` doesn't fit). Generating to it would be a correctness bug, so
those languages use a code point instead:

| Language | One `char` | Why |
|---|---|---|
| Rust | `char` | already one Unicode scalar value |
| Go | `rune` | the same |
| Swift | `Unicode.Scalar` | `Character` is a grapheme cluster, not one character |
| Java, Kotlin | `int`, a code point | their `char` is a UTF-16 unit |
| C# | `System.Text.Rune` | the same reason |
| Dart | `int`, a rune | the same reason |
| TypeScript, Python | a string of exactly one code point, checked | no character type |

**On the wire** (decided 2026-11-02: per format, at no size or speed cost
against the alternatives). A one-character string carries a length prefix a
single character doesn't need: UTF-8 already says from its first byte how long
a character is. So each format picks its cheapest form:

| Format | One `char` | Size | Instead of |
|---|---|---|---|
| `packed@1` | the raw UTF-8 bytes, no prefix, checked by the strict UTF-8 check | 1–4 bytes | a one-character string, 2–5 bytes |
| `msgpack@1` | a one-character string, so other msgpack tools see text | 2–5 bytes | the code point as an integer, 1–5 bytes: 1 byte smaller for ASCII, but a number to every other tool |
| `json@1` | a one-character string, `"a"` | 3–14 bytes | the code point as a number, `97` |

The per-format choices are proposed; each format's specification records its
own. A fixed 4 bytes in `packed@1` would keep a struct of fixed-size fields
fixed-size, at 3 extra bytes per ASCII character; it isn't proposed.

Adding `char` adds a type to formats that already exist. No existing bytes
change, but a runtime that doesn't know `char` can't read a schema that uses
it, and its support claim says so.

## Issues

- **`string[max 64]` is an array of 64 strings, not a bounded string.** Someone
  meaning "a string of at most 64" may write it. With `string` kept, hover and
  diagnostics say "an array of at most 64 strings", and the docs teach
  `char[max 64]` for a bounded string.
- **`string` takes no bound itself,** because bounds don't go on named types
  ([issue 2](max-only.md#issues-and-resolutions)). A bounded string is always
  spelled `char[…]`.
- **A lone `char` needs its own encoding:** see
  [A single `char`](#a-single-char).

## Open

- ~~**Keep the name `string`, or deprecate it**~~: decided, kept as the name
  for a sequence of characters.
- ~~**How a lone `char` is sent**~~: decided, per format at no size or speed
  cost; the per-format forms are [proposed](#a-single-char).
- ~~**`char[N]` in generated code**~~: decided, the
  [three levels](#generated-code), on the condition that measurement confirms
  no correctness or performance cost.
