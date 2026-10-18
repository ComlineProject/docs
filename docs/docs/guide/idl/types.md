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
