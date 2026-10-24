# Structure

A **structure** (`struct`, also called a *message*) is a named data shape. It
carries typed **fields**.

```ids linenums="1"
struct Message {
    sender: string
    recipient: string
    body: string
    priority: u8
}
```

## Fields

A field is `name: Type`, one per line, in declaration order. A field may be
marked `optional` and may carry a default.

```ids linenums="1"
struct Message {
    body: string
    optional subject: string
    priority: u8 = 1
    language: Language = default
}
```

- **`optional`** — the field may be absent. Without it, the field is required.
- **`= <value>`** — a default. Any value form a [constant](const.md) accepts —
  a literal, another constant by name, a `::`-path, or an f-string — plus the
  bare word `default` (the type's own default, e.g. an enum's first variant).
  Non-literals are recorded but not resolved yet.

## Field types

| Kind | Examples |
|---|---|
| integers | `s8 s16 s32 s64`, `u8 u16 u32 u64` |
| floats | `f32`, `f64` |
| other | `bool`, `string` |
| named | another `struct` / `enum`, scoped as `pkg::module::Type` |
| array | `Message[]` (any length), `u8[16]` (fixed) |
| union | `union(string u32)` |

Use `string` for text; `str` and `String` are not Comline types — see
[Text](types.md#text-string).

## Docstrings

A [docstring](docstrings.md) (`///` lines) and `@key=value` annotations attach to
a struct or an individual field.

```ids linenums="1"
/// A message routed through the mail protocol.
struct Message {
    body: string

    /// Shown in the client's list view.
    optional subject: string
}
```


## Annotations

An annotation's value is one of three forms:

- **A single value:** an integer, a string, `true`/`false` or a name
  (`@timeout_ms = 1000`).
- **A list of calls,** for [`@validators`](validator.md)
  (`@validators = [StringBounds(min_chars = 3)]`).
- **A dictionary of `key = value` entries,** for an annotation with several
  settings, such as
  [`@framing`](protocol.md#annotations)
  (`@framing = { name = "jsonrpc", method_names = qualified }`).

```ids
struct Message {
    @optional // <- This is an annotation
    body: string
}
```

TODO: annotations might not apply to structures, only fields

