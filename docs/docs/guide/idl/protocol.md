# Protocol

A **protocol** — a *service* in Protobuf, an *interface* in Cap'n Proto — is a
set of **functions** a caller can invoke.

``` py linenums="1"
protocol Mail {
    function send_message(message: Message) -> bool;
    function fetch_inbox() -> Message[];
    function poke();
}
```

## Functions

```
function NAME( [args] ) [-> ReturnType] [! ErrorName] ;
```

- **Arguments** are `Type` or `name: Type`, comma-separated:
  `function send(Message)` or `function send(msg: Message)`.
- **Return** is `-> Type`; omit it for a one-way call.
- **`! ErrorName`** declares that the function can raise a given `error`.
- Every function ends with `;`.

``` py linenums="1"
/// Mail API for sending and receiving messages.
protocol Mail {

    @timeout_ms=1000
    function send_message(message: Message) -> str ! RecipientNotFound;
}
```

Functions take [docstrings](docstrings.md) (including the `/// @name:` form for
arguments) and `@key=value` annotations.

How a call travels between caller and implementation is the
[runtime](../runtime/index.md)'s job, over a pluggable
[call system](../runtime/call-system.md).
