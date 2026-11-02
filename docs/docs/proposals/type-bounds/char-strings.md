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
- **`char[]` is a string,** and `string` is the built-in name for it. Existing
  schemas keep writing `string`.
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
- **Generated types:**
  - `char[]` with any bound is the language's native string: `String` or
    `&str` in Rust, `string` in TypeScript, with the bound checked.
  - A lone `char` is the language's character type where it has one (`char`
    in Rust), else a one-character string.
  - A generator may use a fixed-capacity type for `char[N]` or `char[max N]`
    only when its configuration opts in
    ([issue 11](max-only.md#issues-and-resolutions)).

## Issues

- **`string[max 64]` is an array of 64 strings, not a bounded string.** Someone
  meaning "a string of at most 64" may write it. Hover and diagnostics say "an
  array of at most 64 strings", and the docs teach `char[max 64]` for a bounded
  string. Whether to go further is open (below).
- **`string` takes no bound itself,** because bounds don't go on named types
  ([issue 2](max-only.md#issues-and-resolutions)). A bounded string is always
  spelled `char[…]`.
- **A lone `char` needs its own encoding** (open, below).

## Open

- **Keep the name `string`, or deprecate it** in favour of `char[]`. Keeping
  it is friendlier and breaks nothing. Deprecating it removes the
  `string[max 64]` mix-up, at the price of writing `char[max 32][max 10]` for
  what is now `string[max 10]` with bounded strings.
- **How a lone `char` is sent:**
  - as a one-character string in every format, the same as `char[1]`; simplest
    and consistent;
  - or as its code point, a `u32`, in `packed@1`; fixed size, but a second
    representation.
- **`char[N]` in generated code:** a native string checked to N characters by
  default, or a fixed array of characters when opted in.
