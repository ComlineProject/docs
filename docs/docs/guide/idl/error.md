# Errors

An **error** is a named failure a [protocol](protocol.md) function can raise. It
has a required `message` and, optionally, fields.

``` py linenums="1"
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

## Fields

After `message`, an error takes [fields](structure.md#fields) exactly like a
[struct](structure.md) — typed, optionally `optional`, with defaults and
docstrings. They carry the data the `message` placeholders read.

## Raising one

A function declares the errors it can raise with `! ErrorName`:

``` py linenums="1"
protocol Mail {
    function send(message: Message) -> bool ! RecipientNotFound;
}
```

This is a bare reference — binding values into the error's fields at the raise
site is not part of the language yet.
