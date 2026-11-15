# Lockstep `datagram`: client & server

A protocol on the lockstep `datagram` framing (`@framing = "datagram"`) gets a
client and a server. This page is only that case; every other protocol runs on a
[connection](connections.md), the default, with its own `serve` and `connect`
([What you use](index.md#what-you-use) says which is which). This page assumes
a schema like [Protocols](../../guides/idl/protocol.md)'s `Mail` example has
been generated to TypeScript:

```ids
@framing = "datagram"
protocol Mail {
    @timeout_ms = 1000
    function send_message(message: Message) -> string ! RecipientNotFound;
    function fetch_inbox() -> Message[];
}
```

## What codegen emits

Full details are [Code generation](../../guides/codegen/index.md)'s job, not
this page's — but the shapes below are what the generated file actually
contains, so the rest of this page can refer to them by name.

```typescript
/** Canonical digest of the frozen IR this file was generated from — the
*  two ends of a connection must agree on it. */
export const IR_HASH = 0x7ea94b595fcf4393n;

/** The package's wire format (`wire.format`): what this file's helpers
*  encode with, and what the peer has to speak too. */
export const Format: Codec = new PackedCodec();

export interface Message {
    body: string;
}

export const MessageLayout: Layout = { struct: [["body", "string"]] };

export class RecipientNotFoundError extends Error {
    static readonly ordinal = 0;
    readonly data: RecipientNotFound;
    constructor(data: RecipientNotFound) { /* … */ }
}

export interface MailSendMessageParams {
    message: Message;
}

/** @internal */
export const MailSendMessageParamsLayout: Layout = { struct: [["message", () => MessageLayout]] };

export interface Mail {
    /** @throws {RecipientNotFoundError} */
    send_message(params: MailSendMessageParams): Promise<string>;
    fetch_inbox(): Promise<Message[]>;
}

/** @internal */
export const MAIL_CALLS = ["send_message", "fetch_inbox"] as const;

export class MailDispatcher implements Dispatch {
    constructor(impl: Mail) { /* … */ }
    // …
}

export class MailClient {
    constructor(client: Client) { /* … */ }

    static async connect(transport: Transport, codec: Codec = Format, framing: Framing = new DatagramFraming()): Promise<MailClient> {
        return new MailClient(await Client.connect(transport, codec, IR_HASH, framing));
    }

    async send_message(params: MailSendMessageParams): Promise<string> { /* … */ }
    async fetch_inbox(): Promise<Message[]> { /* … */ }
}

export function serveMail(impl: Mail, transport: Transport, codec: Codec = Format, framing: Framing = new DatagramFraming()): Promise<void> {
    return new Server(new MailDispatcher(impl), codec, framing).serve(transport, IR_HASH);
}
```

A lockstep protocol's file has no entry-point comment; in `lib` mode the
package's `index.ts` lists its `serveMail` and `MailClient.connect`.

- A 64- or 128-bit integer is a `bigint`: `number` holds integers exactly only
  up to 2^53, and a constant of one is written `7n`, as `IR_HASH` is. `Message`
  has none, but a `u64` field would be a `bigint`. Every type gets a `Layout` of
  the same name plus `Layout` (`MessageLayout`), which the generated client and
  dispatcher pass to the codec: it reads a `u64` as a `bigint`, and says how
  wide each integer is.
- `Mail` is the interface your implementation fills in — every method
  `async`/`Promise`-returning, a thrown `*Error` class per declared `!`
  (several, comma-separated, if the function lists several).
- `MailDispatcher` wraps an implementation and implements the runtime's
  `Dispatch` interface.
- `MailClient` wraps a `Client` and gives you one method per function.
  `@timeout_ms` is not applied by it: the Rust client passes it to
  `call_with_timeout`, and this one makes a plain `call`.
- `serveMail` is the generated convenience function: build a
  `MailDispatcher`, run the handshake, serve. There's no dispatcher
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
import { MailClient, serveMail } from "./generated/mail.js";

const [clientSide, serverSide] = duplex();

serveMail(new MyMail(), serverSide);

const client = await MailClient.connect(clientSide);
const receipt = await client.send_message({ message: { body: "hello" } });
const inbox = await client.fetch_inbox();
```

Both encode with the package's `Format` unless given another `Codec`.
`MailClient.connect` builds a `Handshake` from `IR_HASH` and the codec's
name, sends it, reads the peer's, and rejects with
`RuntimeError.handshake()` on a mismatch — the same check the Rust runtime
does, byte-compatible with it (see [Framing & wire
format](framing-and-wire-format.md)).

A thrown schema error comes back as its generated `*Error` class, so a
normal `try`/`catch` (or `instanceof`) handles it:

```typescript
try {
    await client.send_message({ message: { body: "" } });
} catch (e) {
    if (e instanceof RecipientNotFoundError) {
        console.log("no such recipient");
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
    await client.fetch_inbox();
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
import { serveMail } from "./generated/mail.js";

class MyMail implements Mail {
    async send_message(params: MailSendMessageParams): Promise<string> {
        if (!params.message.body) throw new RecipientNotFoundError({});
        return `sent: ${params.message.body}`;
    }
    async fetch_inbox(): Promise<Message[]> { return []; }
}

await serveMail(new MyMail(), transport);
```

Like the Rust runtime, there's no listener/accept loop built in —
`serveMail` (and the lower-level `Server` class it wraps) serves **one**
already-connected `Transport` until it closes. Accepting multiple
connections concurrently is ordinary `Promise`-based concurrency on your
side: call `serveMail` once per connection and let them run.

For manual control over the handshake, the `Server` class underneath
exposes `serveOne` (one call), `serveUnverified` (loop, no handshake),
and `serve(transport, irHash, handshake?)` (the handshake, `comline@1`
unless given, then the loop) — `serveMail` is just `serve` with the
dispatcher and `IR_HASH` already filled in for you.
