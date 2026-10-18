# Types

Primitives:

| Group | Types |
|---|---|
| signed integers | `s8` `s16` `s32` `s64` |
| unsigned integers | `u8` `u16` `u32` `u64` |
| floats | `f32` `f64` |
| boolean | `bool` |
| text | `string` (see below) |

Plus any `struct` / `enum` name (scoped: `pkg::module::Type`), arrays (`Type[]`
or fixed `Type[10]`), and unions (`union(TypeA TypeB)`).

### Text: `string`

- **`string`** is the text type: UTF-8, any length.
- **`str`** was an accepted spelling until it was removed. Writing it is now a
  build error that tells you to use `string`.
- **`String`** (capitalised) is **not** Comline syntax. It is the Rust type that
  `string` generates into, so you see it in generated Rust, never in a `.ids`
  file. Writing it gets the same hint.

## Type aliases

`type NAME = TYPE` gives a type a second name:

```ids
type UserId = u64
type Handle = string

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
| `s8` … `s64` | `i8` … `i64` | `number` |
| `u8` … `u64` | `u8` … `u64` | `number` |
| `f32` / `f64` | `f32` / `f64` | `number` |
| `bool` | `bool` | `boolean` |
| `string` | `String` | `string` |
| `Message` | `Message` | `Message` |
| `Message[]` | `Vec<Message>` | `Message[]` |
| `u8[16]` | `[u8; 16]` | `number[]` |
| `union(string u32)` | not supported yet | `string \| number` |
| `optional x: T` | `Option<T>` | `x?: T` |

TypeScript's `number` holds integers exactly only up to 2^53, so an `s64` or
`u64` above that loses precision there.

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
