# Types

The built-in types of the schema language. What they become in each
language is in [the guide](../../../guides/idl/types.md#in-generated-code), and
their bytes are in each [format](../../wire/formats/index.md). Bounds
(`T[max N]`) are covered in [the guide](../../../guides/idl/types.md#bounds).

## `bool` { #bool }

`true` or `false`, the only two literals of the type.

## Integers

### Unsigned { #unsigned }

| Type | Range |
| --- | --- |
| <span id="u8"></span>`u8` | 0 to 255 |
| <span id="u16"></span>`u16` | 0 to 65 535 |
| <span id="u32"></span>`u32` | 0 to 2^32 − 1 |
| <span id="u64"></span>`u64` | 0 to 2^64 − 1 |
| <span id="u128"></span>`u128` | 0 to 2^128 − 1 |

### Signed { #signed }

Two's complement.

| Type | Range |
| --- | --- |
| <span id="s8"></span>`s8` | −128 to 127 |
| <span id="s16"></span>`s16` | −32 768 to 32 767 |
| <span id="s32"></span>`s32` | −2^31 to 2^31 − 1 |
| <span id="s64"></span>`s64` | −2^63 to 2^63 − 1 |
| <span id="s128"></span>`s128` | −2^127 to 2^127 − 1 |

Signed integers are written `s`, not `i`: `i32` is not Comline syntax.

## Floats { #floats }

| Type | Precision |
| --- | --- |
| <span id="f32"></span>`f32` | IEEE 754 single precision |
| <span id="f64"></span>`f64` | IEEE 754 double precision |

## Text: `string` and `char` { #text-string-and-char }


- <span id="char"></span>**`char`** is one Unicode scalar value: a single character, not a byte or a
  UTF-16 unit. Its literal is a string of exactly one character, `"a"`; any
  other length is a build error.
- <span id="string"></span>**`string`** is the text type: UTF-8, the built-in name for `char[]`. An
  array of `char` is always text, so `char[max 64]` is a string of at most 64
  characters, not a list of 64 `char` values.
- **`str`** was an accepted spelling until it was removed. Writing it is now a
  build error that tells you to use `string`.
- **`String`** (capitalised) is **not** Comline syntax. It is the Rust type that
  `string` generates into, so you see it in generated Rust, never in a `.ids`
  file. Writing it gets the same hint.

## `()` { #unit }

The unit type: no value, and no bytes on the wire. It's what a function that
waits for its provider but returns nothing gives back, `-> ()`, unlike a
function with no `->`, which gets no reply at all
([One-way, or acknowledged](../../../guides/idl/protocol.md#one-way-or-acknowledged)).
