# Lockstep `datagram`: client & server

A protocol on the lockstep `datagram` framing (`@framing = "datagram"`) gets a
client and a server. This page is only that case; every other protocol runs on a
[connection](connections.md), the default, with its own `serve` and `connect`
([What you use](index.md#what-you-use) says which is which). This page
follows the runtime's own test fixture — a lockstep `Chat` protocol with a
throwing call, a plain call, a `()` return, and a one-way call:

```ids
struct Message {
    body: string
    seq: u64
}

error Rejected {
    reason: string
}

@framing = "datagram"
protocol Chat {
    function send(text: string) -> Message ! Rejected;
    function history(limit: u32) -> Message[];
    function wipe();
    function note(text: string);
}
```

## What codegen emits

```typescript
/** Canonical digest of the frozen IR this file was generated from — the
*  two ends of a connection must agree on it. */
export const IR_HASH = 0x222ffe8dc03c4d62n;

/** The package's wire format (`wire.format`): what this file's helpers
*  encode with, and what the peer has to speak too. */
export const Format: Codec = new PackedCodec();

export interface Message {
    body: string;
    seq: bigint;
}

export const MessageLayout: Layout = { struct: [["body", "string"], ["seq", "u64"]] };

export class RejectedError extends Error {
    static readonly ordinal = 0;
    readonly data: Rejected;
    constructor(data: Rejected) { /* … */ }
}

export interface ChatSendParams {
    text: string;
}

/** @internal */
export const ChatSendParamsLayout: Layout = { struct: [["text", "string"]] };

// … ChatHistoryParams and ChatNoteParams, and their layouts, the same way.

export interface Chat {
    /** @throws {RejectedError} */
    send(params: ChatSendParams): Promise<Message>;
    history(params: ChatHistoryParams): Promise<Message[]>;
    wipe(): Promise<void>;
    note(params: ChatNoteParams): Promise<void>;
}

/** @internal */
export const CHAT_CALLS = ["send", "history", "wipe", "note"] as const;

export class ChatDispatcher implements Dispatch {
    constructor(impl: Chat) { /* … */ }
    // …
}

export class ChatClient {
    constructor(client: Client) { /* … */ }

    static async connect(transport: Transport, codec: Codec = Format, framing: Framing = new DatagramFraming()): Promise<ChatClient> {
        return new ChatClient(await Client.connect(transport, codec, IR_HASH, framing));
    }

    async send(params: ChatSendParams): Promise<Message> { /* … */ }
    async history(params: ChatHistoryParams): Promise<Message[]> { /* … */ }
    async wipe(): Promise<void> { /* … */ }
    async note(params: ChatNoteParams): Promise<void> { /* … */ }
}

export function serveChat(impl: Chat, transport: Transport, codec: Codec = Format, framing: Framing = new DatagramFraming()): Promise<void> {
    return new Server(new ChatDispatcher(impl), codec, framing).serve(transport, IR_HASH);
}
```

A lockstep protocol's file has no entry-point comment; in `lib` mode the
package's `index.ts` lists its `serveChat` and `ChatClient.connect`.

- `seq` is a `u64`, so it's a `bigint`. `number` holds integers exactly only
  up to 2^53, so every 64- and 128-bit integer is a `bigint`, and a constant
  of one is written `7n`. Every type gets a `Layout` of the same name plus
  `Layout` (`MessageLayout`), which the generated client and dispatcher pass to
  the codec: it reads a `u64` as a `bigint`, and says how wide each integer is.
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
- `Format` and `IR_HASH` are exported by this file. A package that also has a
  [connection](connections.md) keeps `Format` in a `wire.ts`, and this file
  imports it from there.
- What's marked `@internal` is wire plumbing: exported, so a `Client` and
  `Server` can be wired by hand, and not what you call (`…ParamsLayout`,
  `…_CALLS`).

## Transport today

Only one `Transport` ships: the in-memory `duplex()` pair (two linked
ends — what one sends, the other receives). A stream/TCP transport is
explicitly a later add, called out in the transport module's own doc
comment. Same-process client/server and tests work today; a real network
transport means implementing the two-method `Transport` interface
(`send` / `recv`, both `Promise`-returning) yourself for now.

**When a sender may reuse a frame.** `send(frame)` resolves only once the
transport no longer needs `frame`. After that the sender is free to reuse or
overwrite it, and the runtime does: it keeps pooled arrays for larger frames
and returns each to the pool when `send` resolves. A transport that holds on to
the frame past that point, to queue it or write it later, must copy it first.
`duplex()` copies.

## Connecting a client

```typescript
import { duplex } from "@comline/runtime";
import { ChatClient, serveChat } from "./generated/chat.js";

const [clientSide, serverSide] = duplex();

serveChat(new MyChat(), serverSide);

const client = await ChatClient.connect(clientSide);
const message = await client.send({ text: "hello" });
await client.note({ text: "fire and forget" }); // no response awaited
```

Both encode with the package's `Format` unless given another `Codec`.
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

One bad call doesn't cost the connection: that call is answered with the
failure, and the next one still works.

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

await serveChat(new MyChat(), transport);
```

Like the Rust runtime, there's no listener/accept loop built in —
`serveChat` (and the lower-level `Server` class it wraps) serves **one**
already-connected `Transport` until it closes. Accepting multiple
connections concurrently is ordinary `Promise`-based concurrency on your
side: call `serveChat` once per connection and let them run.

For manual control over the handshake, the `Server` class underneath
exposes `serveOne` (one call), `serveUnverified` (loop, no handshake),
and `serve(transport, irHash, handshake?)` (the handshake, `comline@1`
unless given, then the loop) — `serveChat` is just `serve` with the
dispatcher and `IR_HASH` already filled in for you.
