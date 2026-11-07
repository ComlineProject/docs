# Transports

A **transport** moves frames between two ends: TCP, a WebSocket, a pipe, a
queue. It doesn't change the bytes a format or framing produce, so it needs no
name, profile or declaration. It is code you pass in at the call site, and the
handshake never sees which one it is.

A transport carries **whole frames**. A medium that has message boundaries
carries one frame per message. A byte stream has none, so it adds a `u32`
little-endian length prefix per frame, as the runtime's own TCP transport does.
The [conformance reference](../../reference/conformance.md#stream-framing)
has the exact rules.

## Rust

Implement `Transport` for blocking use:

```rust
use comline_runtime::contract::RuntimeError;
use comline_runtime::transport::Transport;

impl Transport for Pipe {
    fn send(&mut self, frame: &[u8]) -> Result<(), RuntimeError> {
        self.tx.send(frame.to_vec()).map_err(|_| RuntimeError::Transport)
    }

    fn recv(&mut self, buf: &mut Vec<u8>) -> Result<(), RuntimeError> {
        let frame = self.rx.recv().map_err(|_| RuntimeError::Transport)?;
        buf.clear();
        buf.extend_from_slice(&frame);
        Ok(())
    }
}
```

| Method | Contract |
|---|---|
| `send(&mut self, frame)` | Send one frame. |
| `recv(&mut self, buf)` | Receive the next frame into `buf`, which the caller clears and reuses. Return `Err(RuntimeError::Transport)` once the peer is gone. |
| `recv_timeout(&mut self, buf, timeout)` | Optional. `Ok(true)` if a frame was read, `Ok(false)` if the timeout passed first. The default blocks and ignores the timeout, so a transport with no clock still works but can't honour a per-call deadline. |
| `max_frame(&self)` | Optional. The largest frame you send or receive. Defaults to 16 MiB (`DEFAULT_MAX_FRAME`), the same in every Comline runtime. |

**Frame limits belong to the transport.**

- Sending a frame over the limit is `RuntimeError::FrameTooLarge` with nothing
  written, and the transport keeps working.
- Receiving one is `FrameTooLarge` too, refused before anything is allocated
  for it. On a byte stream you are out of step past it, so close the transport:
  later calls return `RuntimeError::Transport`.

For async code, an `AsyncTransport` is any type that is a `Stream` of
`Result<Vec<u8>, RuntimeError>`, a `Sink<Vec<u8>, Error = RuntimeError>`, and
`Send + Unpin + 'static`. The trait is implemented for every such type, so
there is nothing to implement by name. The stream ends, or yields an error,
once the peer is gone.

For tests, the runtime ships `InMemory` (from `duplex()`) and
`AsyncInMemory` (from `async_duplex()`), which hold frames to the same limit a
socket does.

## TypeScript

```ts
interface Transport {
  send(frame: Uint8Array): Promise<void>;
  recv(): Promise<Uint8Array>;
}
```

- **`send` lends the frame until its promise settles.** Resolve only once the
  transport no longer needs `frame`: it is written out, or copied if you queue
  it or hand it on. The caller may reuse or overwrite the buffer the moment
  `send` settles, so the runtime can encode the next frame into the same one.
- **`recv` resolves with the next frame**, which then belongs to its receiver;
  don't touch it again. Reject with `RuntimeError("transport")` once the peer
  is gone and the queue is drained.
- Each `send` delivers exactly one frame to the peer's next `recv`. A stream
  transport has to add its own boundaries.

The built-in in-memory transport copies each frame (`frame.slice()`) for
exactly this reason.

## Testing one

- Run a client and a server over your transport and make a call. The
  handshake is the first thing to cross it.
- Send a frame over the limit and check the error is
  `FrameTooLarge` and the transport still works (Rust).
- Close one end and check the other fails with a transport error instead of
  hanging.
