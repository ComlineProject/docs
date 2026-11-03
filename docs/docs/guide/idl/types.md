# Types

Primitives:

| Group | Types |
|---|---|
| signed integers | `s8` `s16` `s32` `s64` `s128` |
| unsigned integers | `u8` `u16` `u32` `u64` `u128` |
| floats | `f32` `f64` |
| boolean | `bool` |
| text | `string`, `char` (see below) |

Plus any `struct` / `enum` name (scoped: `pkg::module::Type`), arrays (`Type[]`,
`Type[max 100]` or fixed `Type[10]`), and unions (`union(TypeA TypeB)`).

Every string and every dynamic array needs a [maximum](#bounds), written in its
type or given by a [setting](settings.md#default-maximums). The examples in this guide
carry maxima so they build as written; a bare `string` or `T[]` in one of your
schemas builds only once a default is set.

### Text: `string` and `char`

- **`char`** is one Unicode scalar value: a single character, not a byte or a
  UTF-16 unit. Its literal is a string of exactly one character, `"a"`; any
  other length is a build error.
- **`string`** is the text type: UTF-8, the built-in name for `char[]`. An
  array of `char` is always text, so `char[max 64]` is a string of at most 64
  characters, not a list of 64 `char` values.
- **`str`** was an accepted spelling until it was removed. Writing it is now a
  build error that tells you to use `string`.
- **`String`** (capitalised) is **not** Comline syntax. It is the Rust type that
  `string` generates into, so you see it in generated Rust, never in a `.ids`
  file. Writing it gets the same hint.

## Bounds

A **maximum** says how big a value may be, in its type, so a decoder can refuse
an oversized value before it allocates one. It is written `max N` inside the
brackets, and counts items, or characters for a string:

```ids
struct Customer {
    name: char[max 32]           // a string of at most 32 characters
    code: char[8]                // a string of exactly 8 characters
    orders: Order[max 100]       // at most 100 orders
    tags: char[max 32][max 10]   // at most 10 tags, each at most 32 characters
    ids: u64[16]                 // exactly 16 (a fixed array, as always)
}
```

- **`T[N]`** is exactly `N`. **`T[max N]`** is at most `N`. `T[]` writes no
  maximum, and needs one from a setting.
- **Only a maximum.** A minimum ("not empty", "at least one") is a
  [validator](validator.md#the-standard-validators): `NonEmpty`, `MinChars`,
  `MinItems`. So is a range of values, `IntRange`.
- **`N` is an integer or a [constant](const.md#sizes-from-constants):**
  `char[max NAME_MAX]`. It is at least 1 and at most `u32::MAX` (4294967295);
  `max 0`, an exact length of 0 and a negative size are build errors.
- **`max` is a keyword only right after `[`.** Anywhere else it is an ordinary
  name, so a field called `max` is fine.
- **Only strings and dynamic arrays take one.** Integers, floats, `bool`, enums,
  structs, unions and `()` don't. `string[max 10]` is ten strings, each at the
  package default; for a bounded string write `char[max N]`.
- **Any change to a maximum is breaking**: tightening breaks old senders and
  loosening breaks old receivers.

### Every string and list has a maximum

A schema builds only when every string and dynamic array, at every position
(field, argument, return, alias, union member), has a maximum, from the first of:

1. the position itself, `char[max 64]`;
2. a [default from settings](settings.md#default-maximums), `bounds.string.max`
   for strings and `bounds.array.max` for lists, stored resolved at each
   position it reaches;
3. a give-up: [`@unverified`](protocol.md#giving-up-a-guarantee) on every
   protocol that reaches the position, which gives up bounded size.

There is no built-in default, so a position with none of these is an error that
names it and the fix:

```
struct `Greeting`, field `message`: `string` has no maximum
  Help: write `char[max N]`, or set `bounds.string.max` in settings
```

A position no protocol reaches, such as a type another package can use, has to
be bounded. A struct that can contain itself also needs a
[depth limit](annotations.md#max_depth).

A package default reaches only its own positions: a dependency's types keep
the maxima resolved in the dependency.

### Using a bounded alias

A [type alias](#type-aliases) carries its bound, and the limit is changed
there. Where an alias of a string or of a dynamic array is used (a field,
argument, return or union member), it takes **no `[…]` suffix** of its own:

```ids
type Name = char[max 32]
type Names = Name[max 10]    // a list of an alias is its own alias

struct Customer {
    name: Name               // fine
    nicknames: Names         // fine
    others: Name[max 5]      // error: `Name` is an alias of a string, which
                             // takes no `[…]` where it's used
}
```

The error suggests the alias to declare instead. The rule covers aliases of
strings and dynamic arrays; an alias of a number or a struct keeps the suffix
(`UserId[max 10]`), and the built-in `string` is exempt (`string[max 10]`).
Writing an alias in a list inside another alias, as `Names` does, is allowed.

## Type aliases

`type NAME = TYPE` gives a type a second name:

```ids
type UserId = u64
type Handle = char[max 32]

struct User {
    id: UserId
    handle: Handle
}
```

An alias is transparent: `UserId` is a `u64` everywhere, in the wire format and
in generated code (`pub type UserId = u64;`, `export type UserId = number;`).
An alias can name another alias.

An alias can carry [`@validators`](validator.md#on-a-type-alias), which then
check every value of it, and `@deprecated`, which warns wherever it's used.

## In generated code

| Comline | Rust | TypeScript |
|---|---|---|
| `s8` … `s32` | `i8` … `i32` | `number` |
| `u8` … `u32` | `u8` … `u32` | `number` |
| `s64`, `s128` | `i64`, `i128` | `bigint` |
| `u64`, `u128` | `u64`, `u128` | `bigint` |
| `f32` / `f64` | `f32` / `f64` | `number` |
| `bool` | `bool` | `boolean` |
| `string`, `char[max N]` | `String` | `string` |
| `char` | not supported yet | not supported yet |
| `Message` | `Message` | `Message` |
| `Message[]` | `Vec<Message>` | `Message[]` |
| `u8[16]` | `[u8; 16]` | `number[]` |
| `union(string u32)` | not supported yet | `string \| number` |
| `optional x: T` | `Option<T>` | `x?: T` |

A maximum is in the stored schema and part of a package's version, but
generated code doesn't enforce it yet: a bounded string is a `String` or
`string`, and a bounded list a `Vec` or an array. Checks while decoding and
encoding come with the runtimes, and both generators refuse a single `char`
until a wire format carries one. Each generator's state is on the
[language support](../../reference/languages/index.md) page.

TypeScript's `number` holds integers exactly only up to 2^53, so the 64- and
128-bit integers are `bigint` there, in generated types and in both codecs.

### Fixed arrays

A fixed array keeps its length: in Rust it's always `[T; N]`. TypeScript has
no fixed-length array short of a tuple, so there it's `T[]`, and the length
isn't checked. Fixed and dynamic arrays encode the same way on the wire.

Rust's serde derive only handles arrays up to 32 elements. Longer ones go
through [`serde-big-array`](https://crates.io/crates/serde-big-array):

- As a struct or error field's own type (`hash: u8[64]`), the field gets
  `#[serde(with = "serde_big_array::BigArray")]`. In `lib` mode the generated
  `Cargo.toml` already has `serde-big-array = "0.5"`. In `code` mode the file
  starts with a comment naming that line for you to add.
- Anywhere else, the Rust generator refuses it with an error naming the spot:
  an `optional` field, an element of another array, a function argument or
  return, a `type` alias target. Wrap the array in a struct field instead.

Changing a fixed array's length (`u8[4]` → `u8[8]`) is a breaking change, the
same as changing `f32` to `f64`.

### Unions

TypeScript renders a union as `A | B`. The Rust generator doesn't render
unions yet: it stops with an error naming the field, argument or return that
uses one, rather than generating code that won't compile
([comline-rust#51](https://github.com/ComlineProject/comline-rust/issues/51)).
