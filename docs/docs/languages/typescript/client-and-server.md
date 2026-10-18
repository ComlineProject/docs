# Client & server

This page follows the runtime's own test fixture — a `Chat` protocol with
a throwing call, a plain call, a `()` return, and a one-way call:

```ids
struct Message {
    body: string
    seq: u64
}

error Rejected {
    reason: string
}

protocol Chat {
    function send(text: string) -> Message ! Rejected;
    function history(limit: u32) -> Message[];
    function wipe();
    function note(text: string);
}
```

## What codegen emits

```typescript
export interface Message { body: string; seq: number; }
export class RejectedError extends Error {
    static readonly ordinal = 0;
    constructor(readonly data: Rejected) { … }
}

export interface Chat {
    /** @throws {RejectedError} */
    send(params: ChatSendParams): Promise<Message>;
    history(params: ChatHistoryParams): Promise<Message[]>;
    wipe(): Promise<void>;
    note(params: ChatNoteParams): Promise<void>;
}

export class ChatDispatcher implements Dispatch { constructor(private readonly impl: Chat) {} … }
export class ChatClient { … }
export function serveChat(impl: Chat, transport: Transport, codec: Codec, framing?: Framing): Promise<void>;

export const IR_HASH = 0x…n;  // schema fingerprint, used in the handshake
```

- `Chat` is the interface your implementation fills in — every method
  `async`/`Promise`-returning, a thrown `*Error` class per declared `!`
  (several, comma-separated, if the function lists several).
- `ChatDispatcher` wraps an implementation and implements the runtime's
  `Dispatch` interface.
- `ChatClient` wraps a `Client` and gives you one method per function.
- `serveChat` is the generated convenience function: build a
  `ChatDispatcher`, run the handshake, serve. There's no dispatcher
  "class method" for this — it's a standalone function alongside the
  classes.

## Transport today

Only one `Transport` ships: the in-memory `duplex()` pair (two linked
ends — what one sends, the other receives). A stream/TCP transport is
explicitly a later add, called out in the transport module's own doc
comment. Same-process client/server and tests work today; a real network
transport means implementing the two-method `Transport` interface
(`send` / `recv`, both `Promise`-returning) yourself for now.

## Connecting a client

```typescript
import { duplex, JsonCodec } from "@comline/runtime";
import { ChatClient, serveChat } from "./generated/chat.js";

const [clientSide, serverSide] = duplex();

serveChat(new MyChat(), serverSide, new JsonCodec());

const client = await ChatClient.connect(clientSide, new JsonCodec());
const message = await client.send({ text: "hello" });
await client.note({ text: "fire and forget" }); // no response awaited
```

`ChatClient.connect` builds a `Handshake` from `IR_HASH` and the codec's
name, sends it, reads the peer's, and rejects with
`RuntimeError.handshake()` on a mismatch — the same check the Rust runtime
does, byte-compatible with it (see [Framing & wire
format](framing-and-wire-format.md)).

A thrown schema error comes back as its generated `*Error` class, so a
normal `try`/`catch` (or `instanceof`) handles it:

```typescript
try {
    await client.send({ text: "" });
} catch (e) {
    if (e instanceof RejectedError) {
        console.log("rejected:", e.data.reason);
    } else {
        throw e; // a RuntimeError, or something else entirely
    }
}
```

### When the provider fails outside its schema

A handler can throw something the schema never declared — a dead database,
a bug. That reaches the caller as `RuntimeError` with kind `"provider"`,
and nothing else: no message, no stack, no class. There is no wire
representation for arbitrary provider detail, and inventing one would
publish your internals to everyone who calls you.

```typescript
try {
    await client.history({ limit: 10 });
} catch (e) {
    if (e instanceof RuntimeError && e.is("provider")) {
        // the call reached the provider and it broke; retrying may help
    }
}
```

This is why a function that declares no `!` is still worth calling
defensively — and why it needs no `!` to be able to fail. Declare a `!`
for the failures a caller should *handle*; leave the rest to this channel.

It also means one bad call no longer costs the connection. Before, a
handler that threw something undeclared unwound the server loop: the
connection died and the caller, who was never sent a frame, waited out its
timeout instead. Now that call is answered and the next one still works.

## Serving

```typescript
import { serveChat } from "./generated/chat.js";

class MyChat implements Chat {
    async send(params: ChatSendParams): Promise<Message> {
        if (!params.text) throw new RejectedError({ reason: "empty message" });
        return { body: params.text, seq: 1n };
    }
    async history(): Promise<Message[]> { return []; }
    async wipe(): Promise<void> {}
    async note(): Promise<void> {}
}

await serveChat(new MyChat(), transport, new JsonCodec());
```

Like the Rust runtime, there's no listener/accept loop built in —
`serveChat` (and the lower-level `Server` class it wraps) serves **one**
already-connected `Transport` until it closes. Accepting multiple
connections concurrently is ordinary `Promise`-based concurrency on your
side: call `serveChat` once per connection and let them run.

For manual control over the handshake, the `Server` class underneath
exposes `serveOne` (one call), `serve` (loop, no handshake), and
`serveHandshaked` (handshake, then `serve`) — `serveChat` is just
`serveHandshaked` with the dispatcher and `Handshake` already built for
you.
