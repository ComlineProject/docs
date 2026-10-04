# Types

Primitives:

| Group | Types |
|---|---|
| signed integers | `s8` `s16` `s32` `s64` |
| unsigned integers | `u8` `u16` `u32` `u64` |
| floats | `f32` `f64` |
| boolean | `bool` |
| text | `str` (see below) |

Plus any `struct` / `enum` name (scoped: `pkg::module::Type`), arrays (`Type[]`
or fixed `Type[10]`), and unions (`union(TypeA TypeB)`).

### `str` vs `string` vs `String`

- **`str`** — the text type. Use this. It is what the examples and the
  compiler's diagnostics treat as canonical.
- **`string`** — currently an accepted **synonym** for `str`: it parses,
  validates, and generates identically. The compiler nudges you toward `str`
  (`did you mean 'str'?`). Whether `string` is kept, removed, or given a distinct
  meaning later is unsettled — prefer `str`.
- **`String`** (capitalised) — **not** Comline syntax. It is the Rust type that
  `str` generates into, so you see it in generated Rust, never in a `.ids` file.
