# Structure

A **structure** (`struct`, also called a *message*) is a named data shape. It
carries typed **fields**.

```ids linenums="1"
struct Message {
    sender: char[max 64]
    recipient: char[max 64]
    body: char[max 4096]
    priority: u8
}
```

## Fields

A field is `name: Type`, one per line, in declaration order. A field may be
marked `optional` and may carry a default.

```ids linenums="1"
struct Message {
    body: char[max 4096]
    optional subject: char[max 128]
    priority: u8 = 1
    language: Language = default
}
```

- **`optional`** — the field may be absent. Without it, the field is required.
- **`= <value>`** — a default. Any value a [constant](const.md) accepts — a
  literal, a constant by name, or an integer type's bound (`u16::MAX`) — plus
  the bare word `default` (the type's own default, e.g. an enum's first
  variant). It has to fit the field's type, through any `type` alias: a
  `u8 = 300` or a `u8 = LIMIT` where `LIMIT` is 300 is an error.

## Field types

A field can be any [type](types.md): a primitive (`u32`, `bool`, `char[max 64]`), a
`struct`, `enum` or `type` alias by name (scoped as `pkg::module::Type`), an
array (`Message[max 100]`, `u8[16]`) or a union (`union(char[max 64] u32)`).

## Docstrings and annotations

A [docstring](docstrings.md) (`///` lines) documents the struct or a field.
[Annotations](annotations.md) (`@key = value`) above a field attach to it, as
[`@validators`](validator.md) does; above the struct, they attach to the
struct, as `@deprecated` and [`@settings`](settings.md#named-presets-settings)
do.

```ids linenums="1"
/// A message routed through the mail protocol.
@deprecated = "use Envelope"
struct Message {
    /// Plain-text body, UTF-8.
    @validators = [StringBounds(min_chars = 1)]
    body: char[max 4096]

    /// Shown in the client's list view.
    optional subject: char[max 128]
}
```
