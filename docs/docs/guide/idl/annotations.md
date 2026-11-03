# Annotations

An **annotation** is a `@key = value` line placed directly above what it
applies to: a declaration, a field or a function.

```ids linenums="1"
@framing = "jsonrpc"
protocol Mail {
    @timeout_ms = 1000
    function send(message: Message) -> bool;

    @idempotent
    function fetch_inbox() -> Message[max 100];
}
```

## Values

A value takes one of four forms:

| Form | Example |
|---|---|
| none: a bare marker | `@idempotent` |
| a single value: an integer, a string, `true` / `false`, or a name | `@timeout_ms = 1000`, `@provider = Client` |
| a list of calls, for validators | `@validators = [StringBounds(min_chars = 3)]` |
| a dictionary of `key = value` entries | `@framing = { name = "jsonrpc", method_names = qualified }` |

## The annotations Comline knows

Each one is checked: its value against the form it takes, and its place
against where it applies. A wrong value or a misplaced annotation fails the
build.

| Annotation | On | What it does | Details |
|---|---|---|---|
| `@validators` | a field, a `type` alias | runs named checks on the value | [Validators](validator.md#using-one-validators) |
| `@max_depth` | a struct | how deeply a struct that can contain itself nests | [`@max_depth`](#max_depth) |
| `@deprecated` | a struct, a `type` alias | warns wherever it's used; the value is `true` or a message | [Types](types.md#type-aliases) |
| `@settings` | any declaration | applies a named settings preset | [Settings](settings.md#named-presets-settings) |
| `@framing` | a protocol | how calls are framed on the wire | [Protocols](protocol.md#annotations) |
| `@handshake` | a protocol | what runs before the first call | [Protocols](protocol.md#annotations) |
| `@provider` | a protocol | which side implements it: `Server`, `Client` or `Multiple` | [Calls in both directions](protocol.md#calls-in-both-directions) |
| `@consumer` | a protocol | the other side; follows from `@provider` | [Protocols](protocol.md#annotations) |
| `@unverified` | a protocol | gives up a guarantee, with the reason | [Giving up a guarantee](protocol.md#giving-up-a-guarantee) |
| `@timeout_ms` | a function | how long a client waits for the reply; used by generated Rust | [Protocols](protocol.md#functions) |
| `@idempotent` | a function | marks a call as safe to repeat; advisory, nothing reads it yet | |

`@framing` and `@unverified` are off until a package allows them in its
[settings](settings.md#the-built-in-default), since each changes what peers
can rely on.

Any other `@key` is allowed and kept in the frozen schema, so a tool of your
own can read it. Comline doesn't check it.

## `@max_depth`

```ids
@max_depth = 8
struct Comment {
    text: char[max 500]
    replies: Comment[max 20]
}
```

A struct that can contain itself, directly or through other structs, fields,
arrays, unions, optionals or aliases, has no natural end to its size. `@max_depth`
says how many levels deep a value may nest, and a decoder refuses one nested
deeper.

- **The value is an integer.**
- **Every such struct needs one,** or a default from the
  [`bounds.depth.max`](settings.md#default-maximums) setting, which `@max_depth`
  overrides. Without either, the build fails naming the struct:
  `struct `Comment` can contain itself, and has no depth limit`.
- **It is the third way to bound a message:** together with the maxima on
  strings and arrays ([Bounds](types.md#bounds)) it gives every message a
  worst-case size. A protocol that gives up bounded size with
  [`@unverified`](protocol.md#giving-up-a-guarantee) covers a struct it reaches.
- **The limit is stored resolved,** so changing it changes the type.

## In the editor

Hovering an annotation shows what it does, where it applies, its default, and
what reads it. Completion offers the annotations that fit where the cursor is.
