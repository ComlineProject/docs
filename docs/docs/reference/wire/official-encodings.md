# Official encodings

The formats, framings and handshakes every package can name without
declaring them: `packed@1`, `datagram@2`, `comline@1` and the rest. They're
declared by the official encodings package, which is built into the
toolchain the way `std` is. Each declaration comes with a **profile**: the
facts its encoding states about how it encodes, each proven by the
conformance vectors in the runtime's corpus. A package can declare its own
the same way ([Formats and framings](../../guide/extending/encodings.md)).

The tables below are generated from those profiles, as core embeds them.

## What the facts mean

| Fact | Values |
|---|---|
| `struct_fields` | A struct's fields are identified `by_position` or `by_name`. |
| `unknown_field` | A field the reader doesn't know is `rejected` or `ignored`. |
| `missing_optional` | An optional field left out is `rejected` or read as `absent`. |
| `enum_variants` | A variant is identified `by_name` or `by_index`. |
| `unknown_variant` | A variant the reader doesn't know is `rejected` or `tolerated`. |
| `integer_width` | An integer is encoded `by_value` (any width that fits) or at its `exact` width. |
| `calls` | A framing names a call `by_index`, `by_name` or `by_id`. |
| `errors` | A framing names an error `by_ordinal` or `by_name`. |
| `schema_agreement` | The handshake checks both ends were built from compatible schemas. |
| `encoding_agreement` | The handshake checks both ends use the same format and framing. |

## The profiles

<!-- encodings:start -->
<!-- Rendered from ComlineProject/core's official encodings package by scripts/sync-official-encodings.py - don't edit by hand. -->

### Formats

| format | `struct_fields` | `unknown_field` | `missing_optional` | `enum_variants` | `unknown_variant` | `integer_width` |
|---|---|---|---|---|---|---|
| `packed@1` | `by_position` | `rejected` | `rejected` | `by_index` | `rejected` | `exact` |
| `json@1` | `by_name` | `ignored` | `absent` | `by_name` | `rejected` | `by_value` |
| `msgpack@1` | `by_position` | `rejected` | `rejected` | `by_name` | `rejected` | `by_value` |

### Framings

| framing | `calls` | `errors` |
|---|---|---|
| `jsonrpc@1` | `by_name` | `by_ordinal` |
| `datagram@1` | `by_index` | `by_ordinal` |
| `datagram@2` | `by_index` | `by_ordinal` |

### Handshakes

| handshake | `schema_agreement` | `encoding_agreement` | establishes |
|---|---|---|---|
| `comline@1` | true | true | schema agreement, encoding agreement |

<!-- encodings:end -->

## The guarantees they keep

A protocol keeps a [guarantee](../../guide/idl/protocol.md#giving-up-a-guarantee)
when what it uses establishes it:

- **Schema agreement** and **encoding agreement** come from the handshake,
  where its profile states them `true`. `none` isn't declared, because it's the
  absence of a handshake, so it establishes neither.
- **Encoding conformance** holds when the format and framing ship conformance
  vectors. Every official encoding does.
- **Version honesty** is held until releases can lower a bump.

`comline inspect` shows which of these each protocol keeps, and why
([comline inspect](../tools/inspect.md)).

A profile's facts are also what the version comparison will turn into bumps.
That comparison, and a protocol's compatibility facts (its line, version and
shape hash), aren't built yet
([core#119](https://github.com/ComlineProject/core/issues/119)).
