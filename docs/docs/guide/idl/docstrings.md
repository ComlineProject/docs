# Docstrings

A **docstring** is a block of consecutive `///` lines. It attaches to the
declaration immediately below it — a `const`, `struct`, `enum`, `struct` field,
`protocol` or `function`.

``` py linenums="1"
/// Send a message to a recipient.
/// @message: the message to deliver
/// Returns whether delivery succeeded.
function send_message(message: Message) -> bool;
```

Two line forms:

- a plain description line
- `/// @name: description` — documents one field or argument

Both are kept as raw text; the `@name:` form is not parsed into structured data
(so a `Returns …` line is just text, not a special tag). `//` (two slashes) is an
ordinary comment and is discarded.

``` py linenums="1"
/// A message routed through the mail protocol.
struct Message {
    /// Plain-text body, UTF-8.
    body: string
}
```
