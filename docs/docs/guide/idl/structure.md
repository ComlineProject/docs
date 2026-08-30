# Structure

A **structure** (`struct`, also called a *message*) is a named data shape. It
carries typed **fields**.

``` py linenums="1"
struct Message {
    sender: str
    recipient: str
    body: string
    priority: u8
}
```

## Fields

A field is `name: Type`, one per line, in declaration order. A field may be
marked `optional` and may carry a default.

``` py linenums="1"
struct Message {
    body: string
    optional subject: str
    priority: u8 = 1
    language: Language = default
}
```

- **`optional`** — the field may be absent. Without it, the field is required.
- **`= <value>`** — a default: an integer, a string literal, or an identifier
  (`default` selects the type's own default, e.g. an enum's first variant).

## Field types

| Kind | Examples |
|---|---|
| integers | `s8 s16 s32 s64`, `u8 u16 u32 u64` |
| floats | `f32`, `f64` |
| other | `bool`, `str`, `string` |
| named | another `struct` / `enum`, scoped as `pkg::module::Type` |
| array | `Message[]` (any length), `u8[16]` (fixed) |
| union | `union(str u32)` |

## Docstrings and annotations

A [docstring](docstrings.md) (`///` lines) and `@key=value` annotations attach to
a struct or an individual field.

``` py linenums="1"
/// A message routed through the mail protocol.
struct Message {
    body: string

    /// Shown in the client's list view.
    optional subject: str
}
```

Annotation values are simple — an integer, string or identifier (`@internal=true`).
Richer forms such as `@validators=[…]` are still being designed.
