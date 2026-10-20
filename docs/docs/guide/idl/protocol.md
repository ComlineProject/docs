# Protocol

A **protocol** — a *service* in Protobuf, an *interface* in Cap'n Proto — is a
set of **functions** a caller can invoke.

```ids linenums="1"
protocol Mail {
    function send_message(message: Message) -> bool;
    function fetch_inbox() -> Message[];
    function poke();
}
```

## Functions

```
function NAME( [args] ) [-> ReturnType] [! ErrorName, ...] ;
```

- **Arguments** are `Type` or `name: Type`, comma-separated:
  `function send(Message)` or `function send(msg: Message)`.
- **Return** is `-> Type`; omit it for a one-way call.
- **`! ErrorName`** declares that the function can raise a given
  [`error`](error.md). List several, comma-separated, for a function that
  can fail in more than one way: `! NotFound, Denied`. The name must be an
  `error` — a `struct` or `enum` after `!` is a build error, because only
  an `error` has a wire ordinal to travel as.
- Every function ends with `;`.

```ids linenums="1"
/// Mail API for sending and receiving messages.
protocol Mail {

    @timeout_ms=1000
    function send_message(message: Message) -> string ! RecipientNotFound;
}
```

Functions take [docstrings](docstrings.md) (including the `/// @name:` form for
arguments) and `@key=value` annotations.

## Annotations

A `@key=value` annotation on the `protocol` itself configures the whole service.

```ids linenums="1"
@framing = "jsonrpc"
protocol Mail {
    function send_message(message: Message) -> string ! RecipientNotFound;
}
```

- **`@framing`** picks the wire framing the generated client and server use.
  `"jsonrpc"` (`json-rpc`, `jsonrpc-2.0`) emits a
  [JSON-RPC 2.0](https://www.jsonrpc.org/specification) stack; omit it for the
  default compact datagram framing. `"datagram@2"` puts the protocol on a
  [connection](#calls-in-both-directions). Both ends of a connection must
  agree — the [handshake](../runtime/call-system.md) refuses a mismatch.
- **`@provider`** says which side implements the protocol: `Server` (the
  default), `Client` or `Multiple`. See
  [Calls in both directions](#calls-in-both-directions).
- **`@consumer`** is the other side, which follows from `@provider`. You don't
  need to write it, but if you do, it has to agree.
- **`@handshake`** picks what runs on a connection before the first call:
  `"comline@1"` (the default) checks that both ends share the schema, format
  and framing; `"none"` sends and checks nothing. Without it, the protocol takes
  the package's `handshake = "..."` from `config.idp`, else `comline@1`.
- **`@unverified`** says why a protocol gives up a guarantee Comline would
  otherwise give its peers. It's required where one is given up, as with
  `@handshake = "none"`; see [Giving up a guarantee](#giving-up-a-guarantee).

## Calls in both directions

By default the side that dialled calls and the side that accepted answers. A
protocol the client implements turns that round: the server calls it, to push
a message or to ask the client something mid-request.

```ids linenums="1"
@framing = "datagram@2"
protocol Chat {
    function send(text: string) -> u64;
}

@provider = Client
@framing = "datagram@2"
protocol Events {
    function message(text: string) -> bool;
    function ping();
}
```

- **`@provider = Client`**: the client implements it and the server calls it.
  **`@provider = Multiple`**: both sides implement it and either can call.
- **The framing has to tell requests from replies,** since both ends now send
  both. `datagram@1`, the default, can't, so a `Client` or `Multiple`
  protocol without `@framing` is a build error
  (`validation::reverse-calls-need-framing`). Use `@framing = "datagram@2"`.
  Allowing `@framing` is a package setting
  (`annotations.framing.allowed = true`).
- **`@consumer` that disagrees with `@provider`** is a build error
  (`validation::provider-consumer-mismatch`).

Protocols on `datagram@2` run on a **connection** instead of a client and a
server:

- **One connection carries all of them.** Each side provides the protocols it
  implements and calls the others.
- **Calls can nest.** A handler receives the peer that called it, so it can
  call back before it answers. While a side waits for a reply, it keeps
  serving the peer's requests.
- **Each protocol has a number on the wire:** its position among the
  package's protocols, in schema order.
- **A connection keeps typed data of its own** (a session, a user id) that
  every handler on it can reach.

How this looks in code: [Rust](../../languages/rust/connections.md),
[TypeScript](../../languages/typescript/connections.md). Status: generated
for `datagram@2`; JSON-RPC on a connection isn't supported yet
([runtime#19](https://github.com/ComlineProject/runtime/issues/19)).

## Giving up a guarantee

A protocol fronting a peer that can't take part in Comline's handshake (a
legacy service with no schema, say) can run none:

```ids linenums="1"
@handshake = "none"
@unverified = "the 2009 billing gateway has no schema; its version is pinned by contract"
protocol Billing {
    function charge(cents: u64) -> bool;
}
```

Nothing then checks that both ends agree on the schema or the encoding, so the
protocol gives up **schema agreement** and **encoding agreement**. Core works
that out; the schema only says *that* something is unverified and *why*:

- **The marker is required.** Giving a guarantee up without `@unverified` is a
  build error, and the reason can't be empty. A marker on a protocol that gives
  nothing up is a warning.
- **It's off by default,** like `@framing`: a package allows it with
  `settings = { annotations = { unverified = { allowed = true } } }`.
- **Core freezes the set** with the reason. Build output and generated code
  name it ("`Billing` is unverified: schema agreement isn't established
  (handshake `none`)"), each guarantee under its own diagnostic code
  (`unverified::schema-agreement`, …) so an organisation can raise or quiet
  them.
- **Giving one up is a major change;** restoring one is minor.
- **Every consumer accepts it,** under the dependency in its own `config.idp`,
  for exactly the set given up:

  ```
  dependencies = {
      billing = {
          path = "../billing"
          accept_unverified = { Billing = ["schema_agreement", "encoding_agreement"] }
      }
  }
  ```

  Nobody writes this by hand: `comline add` shows what a new dependency gives
  up and asks before writing it, and `comline accept billing` (or
  `billing::Billing`) does the same for one already declared. In the editor,
  the dependency's entry in `config.idp` shows the error, with a quick fix
  that writes the line. Until it's accepted, the build fails, printing the
  entry. The list is a snapshot: if a
  later version of the dependency gives up more, the build stops again until
  `comline accept` is run again.

How a call travels between caller and implementation is the
[runtime](../runtime/index.md)'s job, over a pluggable
[call system](../runtime/call-system.md).
