# Docstrings

A **docstring** is a block of consecutive `///` lines. It attaches to the
declaration immediately below it — a `const`, `struct`, `enum`, `struct` field,
`protocol` or `function`.

```ids linenums="1"
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

```ids linenums="1"
/// A message routed through the mail protocol.
struct Message {
    /// Plain-text body, UTF-8.
    body: string
}
```

## Module docs

A `///` docstring documents the declaration below it, so a *module* (a schema)
and a *package* document themselves with **`//!`** lines at the top of the
file, like Rust's inner doc comments:

```ids linenums="1"
//! Types for talking HTTP: request methods, requests and responses.
//!
//! Plain data types: use them as fields and arguments in your own schemas.

/// An HTTP request method.
enum HttpMethod {
    GET
    POST
}
```

- The header is the `//!` lines before the schema's first declaration. Blank
  lines and plain `//` comments (a license header, say) may come before or
  between them. The first declaration, or a `///` docstring, ends it, and a `//!`
  line after code is an ordinary comment.
- Each line loses its `//!` and one space. Indentation after that stays, so an
  indented block is a code example. Blank `//!` lines separate paragraphs.
- At the top of `config.idp`, the same lines document the package:

  ```idp
  //! The Comline standard library.
  congregation std
  specification_version = 1
  ```
- A directory of schemas has no file of its own. To document `api/`, put the
  docs in `api.ids` next to it.

The editor shows them wherever a path segment is. In
`use std::validators::StringBounds`, hovering `std` shows the package's docs and
the modules in it, and hovering `validators` shows that module's docs and the
types it declares. `use` completion shows the same docs beside each module and
type. Like docstrings, module docs are for readers and tools: they don't change
a build, a version or generated code.

[The standard library](use.md#the-standard-library) documents itself this way.
