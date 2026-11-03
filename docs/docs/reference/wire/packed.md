# `packed@1`

The default wire format: a value is its fields back to back, in declaration
order, like a packed C struct. There's no padding and there are no headers,
names or type tags. The schema already says each field's type and width, so
the bytes don't repeat it.

A package picks its format with `config.idp`'s `wire.format`
([Wire defaults](../../guide/packages/index.md#wire-defaults)); with nothing
declared, it's this one.

## Layout

| Type | Bytes |
|---|---|
| `bool` | 1 byte: `00` or `01`; anything else is an error |
| `u8` `u16` `u32` `u64` `u128` | 1, 2, 4, 8, 16 bytes, little-endian |
| `s8` `s16` `s32` `s64` `s128` | 1, 2, 4, 8, 16 bytes, little-endian two's complement |
| `f32` `f64` | 4, 8 bytes, IEEE 754 little-endian |
| `string`, `char[max N]`, `char[N]` | length in bytes as a varint, then that many bytes of UTF-8 (invalid UTF-8 is an error). An array of `char` is always text, so `char[N]` sends its length too |
| `char` | its UTF-8 bytes alone, 1 to 4, no length: the first byte says how many follow |
| `T[]`, `T[max N]` | element count as a varint, then the elements |
| `T[N]` | the N elements; the length is in the schema (except `char[N]`, above) |
| struct, error body, a call's arguments | the fields in declaration order |
| optional field | `00`, or `01` followed by the value |
| enum | the variant's index in declaration order, as a varint |
| `union(A B ...)` | the member's index in the union, as a varint, then its value |
| `()` | nothing |

**Varints** are unsigned LEB128: 7 bits per byte, low bits first, high bit set
on every byte but the last. Only the shortest encoding is accepted (an
overlong one is an error), so a value has exactly one encoding.

**Decoding is strict.** A value must use all the bytes it was given: trailing
bytes are an error. A length larger than the bytes left is an error before
anything is allocated, so a hostile length can't make the decoder reserve
memory.

## `char` and bounds

**A single `char`** is one Unicode scalar value, sent as its UTF-8 bytes
with no prefix: `61` for `a`, `c3 a9` for `é`, `e2 82 ac` for `€`,
`f0 9f 98 80` for `😀`. The decoder reads the first byte's width and runs
the strict UTF-8 check. It refuses:
- a continuation byte or `c0`, `c1`, `f5`..`ff` in first place;
- an overlong form;
- a surrogate;
- a value past U+10FFFF;
- a character cut short.

**Bounds** (`char[max N]`, `T[max N]`, `@max_depth`) don't change the bytes,
only what a decoder accepts. A value over its bound is refused like
malformed input, and an encoder refuses to write one.

| Bound | Decoding refuses |
|---|---|
| `T[max N]` | a count above N, before anything is allocated |
| `char[max N]` | a byte length above 4 × N before reading the string, since N characters take at most 4 × N bytes; then, during the UTF-8 check, a string of more than N characters. Characters are counted, never bytes, and never normalized |
| `@max_depth = D` | a value of the recursive type nested more than D deep (the outermost is level 1), before reading any deeper |

`"é€😀a"` fits `char[max 4]`: 4 characters in 10 bytes. `"ééééé"` doesn't:
5 characters, though only 10 bytes.

## Example

```ids
enum Class {
    Warrior
    Mage
}

struct Player {
    id: u32
    hp: u16
    name: char[max 32]
    optional guild: char[max 32]
    class: Class
    pos: f32[2]
}
```

`Player { id: 7, hp: 100, name: "ab", guild: none, class: Mage, pos: [1.0, 2.0] }`:

```text
07 00 00 00   id
64 00         hp
02 61 62      name: length 2, "ab"
00            guild: absent
01            class: Mage, index 1
00 00 80 3f   pos[0] = 1.0
00 00 00 40   pos[1] = 2.0
```

That's 19 bytes. The same value in `json@1` is 73.

## Sizes

- **Fixed fields cost their declared width.** A `u64` always takes 8 bytes,
  even holding `1`, so a field that's usually small should be declared
  narrow. Each one is a straight copy, with no branching per byte.
- **Varints only where the schema can't say the size:** lengths, counts, and
  enum and union indexes. These are almost always small, so they usually take
  one byte.

## Evolution

`packed@1` is positional, like `msgpack@1`:

- **Major:** adding, removing or reordering fields (an optional one included),
  or reordering enum variants or union members.
- **Minor:** appending an enum variant. An old peer can't decode the new one,
  so don't send it to one.

Changing a package's `wire.format` is itself a major change.

## In the runtimes

- **Rust:** `comline_runtime::format::Packed`, a `WireFormat` built as a serde
  serializer and deserializer. It needs neither `std` nor an allocator, so it
  works on targets the JSON and MessagePack formats don't.
- **TypeScript:** `PackedCodec`. A JS value doesn't say whether a number is a
  `u16` or an `f64`, so the generator emits a `Layout` per type, which the
  codec walks. `u64`, `s64` and wider are `bigint`.
- **Conformance:** byte-exact vectors in the
  [runtime's wire corpus](https://github.com/ComlineProject/runtime/blob/main/runtime/conformance/vectors/format-packed.json)
  pin each type's bytes and each decoding error, a single `char`, and each
  bound at and over its limit. Both runtimes pass them; see
  [Runtimes side by side](../languages/index.md#runtimes-side-by-side).
