# Protocol

A **protocol** — a *service* in Protobuf, an *interface* in Cap'n Proto — is a
set of functions a caller can invoke. Each function takes typed parameters and
returns a typed result.

``` py linenums="1"
protocol Mail {
    fn send_message(message: Message) -> bool
    fn fetch_inbox() -> Message[]
}
```

Functions carry [docstrings](docstrings.md), and — as the language grows —
attributes for things like streaming, timeouts and provider/consumer direction.
Those are still being designed; see the [proposals](../../proposals/index.md).

How a protocol call actually travels between caller and implementation is the
[runtime](../runtime/index.md)'s job, over a pluggable
[call system](../runtime/call-system.md).
