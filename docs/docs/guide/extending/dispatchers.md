# Dispatchers (middleware)

The **dispatcher** is the provider side of a protocol: given a call and its
encoded params, it runs your handler and records the outcome. The generated
`<Proto>Dispatcher` implements the runtime's `Dispatch` trait, and the server
is generic over it, so you can wrap it. A wrapper that delegates to the
generated one can log, authorise, meter or reject a call before or after it.

It changes nothing on the wire, so it needs no name, profile or declaration.
There is no framework for it: a wrapper is a type that implements the same
trait.

## Rust

```rust
use comline_runtime::contract::{Dispatch, Kind, Peer, Reply, RuntimeError, WireFormat};

/// Logs each call, then hands it on.
pub struct Logged<D>(pub D);

impl<D: Dispatch> Dispatch for Logged<D> {
    fn calls(&self) -> &'static [&'static str] {
        self.0.calls()
    }

    fn dispatch<W: WireFormat>(
        &self,
        call: Kind,
        params: &[u8],
        format: &W,
        reply: &mut Reply,
    ) -> Result<(), RuntimeError> {
        eprintln!("call {call:?}");
        let result = self.0.dispatch(call, params, format, reply);
        eprintln!("-> {:?}", reply.outcome());
        result
    }

    fn dispatch_with<P: Peer>(
        &self,
        call: Kind,
        params: &[u8],
        reply: &mut Reply,
        peer: &mut P,
    ) -> Result<(), RuntimeError> {
        eprintln!("call {call:?}");
        let result = self.0.dispatch_with(call, params, reply, peer);
        eprintln!("-> {:?}", reply.outcome());
        result
    }
}
```

- **`calls`** is the protocol's function names in declaration order. Delegate
  it.
- **`dispatch`** serves a call on a client-and-server pair. `params` is still
  encoded; `reply` is where the result is recorded.
- **`dispatch_with`** serves a call on a `Connection`, with a handle to the peer
  that made it, so a handler can call back. **Forward both.** The default
  `dispatch_with` calls `dispatch`, and a generated dispatcher for a protocol
  on a connection answers `dispatch` with a fault and does its work in
  `dispatch_with`. A wrapper that forwards only `dispatch` would fault every
  call.
- **`reply.outcome()`** tells you what was recorded: `Outcome::Ok`,
  `Outcome::Err(ordinal)`, `Outcome::Fault`, or `Outcome::None` for a one-way
  call.
- **To reject a call**, don't delegate. Call `reply.fault()` and return
  `Ok(())`; the caller sees a provider fault and no detail crosses the wire.
  To refuse with a schema error, you would have to encode the error body
  yourself, so most wrappers fault.

Wire it where you hand the dispatcher over:

```rust
let dispatcher = Logged(FooDispatcher(my_impl));

// A client-and-server pair:
Server::new(dispatcher, format).serve(&mut transport, IR_HASH)?;

// A connection:
conn.provide(FooDispatcher::<MyImpl>::PROTOCOL, dispatcher);
```

The generated `serve` and `provide_on` helpers sit on the generated dispatcher
and build the server themselves, so a wrapped dispatcher goes through
`Server::new` (or `Server::with_framing`) and `Connection::provide` as above.
If the protocol declares a handshake other than `comline@1`, finish with
`serve_with` and that handshake instead of `serve`
([Handshakes](handshakes.md)).

### Async

For an `AsyncConnection`, wrap `AsyncDispatch`. The trait is
`Send + Sync + 'static`, and its `dispatch` returns a future:

```rust
fn dispatch<'a, P: AsyncPeer>(
    &'a self,
    call: Kind,
    params: &'a [u8],
    peer: &'a P,
) -> impl Future<Output = Result<Answer, RuntimeError>> + Send + 'a;
```

An async wrapper delegates the same way, awaits the inner call, and inspects
or replaces the `Answer`. Register it with `AsyncConnection::provide`.

## TypeScript

`Dispatch` is an interface:

```ts
interface Dispatch {
  calls(): readonly string[];
  dispatch(call: Kind, params: Uint8Array, codec: Codec, reply: Reply): Promise<void>;
  dispatchWith?(call: Kind, params: Uint8Array, reply: Reply, peer: Peer): Promise<void>;
}
```

A wrapper holds the generated dispatcher and forwards to it. `dispatchWith` is
optional: without it, a connection calls `dispatch` with the peer's codec. If
the inner dispatcher has one, forward it too.

Give the wrapper to `Server` where you would give the generated dispatcher, or
to `Connection.provide(protocol, dispatcher)`.

## What a wrapper can't do

- It sees `params` as bytes. To look inside, decode them with the format.
- It runs only for calls this side serves. Calls you make as a client go
  through the client, not the dispatcher.
- A helper for composing wrappers is a possible runtime addition; none exists
  today.
