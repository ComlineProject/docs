# Errors

An **error** is a named failure a [protocol](protocol.md) function can raise. It
has a required `message` and, optionally, fields.

```ids linenums="1"
/// Raised when a message is sent to an unknown recipient.
error RecipientNotFound {
    message = "no recipient named {self.name}"
    name: str
}
```

## `message`

A string with `{dotted.path}` **placeholders** that are substituted when the
error is rendered — `{self.name}` reads the error's own `name` field. Write a
literal brace by doubling it: `{{` and `}}`.

`message` is expected on every error.

This is the text a generator renders when a raised error is printed — the
Rust generator builds a `Display` from it, so `{}` on a `RecipientNotFound`
produces `no recipient named ada` rather than a field dump. Write it as the
sentence you would want to read in a log.

## Fields

After `message`, an error takes [fields](structure.md#fields) exactly like a
[struct](structure.md) — typed, optionally `optional`, with defaults and
docstrings. They carry the data the `message` placeholders read.

## Raising one

A function declares the errors it can raise with `! ErrorName`:

```ids linenums="1"
protocol Mail {
    function send(message: Message) -> bool ! RecipientNotFound;
}
```

A function that can fail in more than one way lists them, comma-separated:

```ids linenums="1"
protocol Mail {
    function send(message: Message) -> bool ! RecipientNotFound, QuotaExceeded;
}
```

This is a bare reference — binding values into the error's fields at the raise
site is not part of the language yet.

The name has to resolve to an `error` declared in this schema or brought in
by a [`use`](use.md). Three mistakes are build errors rather
than something you discover in generated code:

| Mistake | Diagnostic |
|---|---|
| the name resolves to nothing | `validation::unresolved-throw` — suggests the closest declared error when it looks like a typo |
| the name is a `struct`, `enum` or other declaration | `validation::throw-not-an-error` |
| the same error listed twice | `validation::duplicate-throw` |

Only an `error` can follow `!` because only an `error` has a slot in the
schema's error space — the ordinal a raised failure actually travels as —
and only an `error` carries the `message` that renders it.

## What a function that raises nothing can still do

Declaring no `!` means the function cannot raise anything *the schema
describes*. It does not mean the implementation cannot fail: a dead
database is not a schema concept, and a provider can always report a
failure outside the schema, which reaches the caller as a generic
"provider failure" with no detail attached. Nothing about it crosses the
wire, so it can never be mistaken for one of your declared errors — and
there is nothing to declare for it.

So add a `!` for the failures a caller should be able to *handle*, and
leave the rest to that channel. See the
[Rust](../../languages/rust/client-and-server.md#error-handling-two-layers)
and [TypeScript](../../languages/typescript/client-and-server.md)
guides for how each one surfaces.
