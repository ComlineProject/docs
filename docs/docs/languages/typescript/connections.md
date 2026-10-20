# Connections

A protocol on `datagram@2`, or one the client provides, runs on a
[connection](../../guide/idl/protocol.md#calls-in-both-directions) instead of
a [client and server](client-and-server.md). This page uses this schema:

```ids
@framing = "datagram@2"
protocol Chat {
    function send(text: string) -> u64;
    function count() -> u64;
}

@provider = Client
@framing = "datagram@2"
protocol Events {
    function message(text: string) -> bool;
    function ping();
}
```

## What codegen emits

```ts
export interface Chat {
  send(peer: Peer, params: ChatSendParams): Promise<bigint>;
  count(peer: Peer): Promise<bigint>;
}

export class ChatDispatcher implements Dispatch {
  static readonly PROTOCOL = 0;
  constructor(impl: Chat);
  provideOn(conn: Connection): void;
}

export class ChatSender {
  constructor(peer: Peer);
  send(params: ChatSendParams): Promise<bigint>;
  count(): Promise<bigint>;
}

// Events, EventsDispatcher (PROTOCOL = 1) and EventsSender, the same way.

export const CONNECTION_IR_HASH = 0x…n;  // checked by the handshake
```

It differs from a client and server in three ways:

- **Handlers take the peer first:** the other end of the connection the call
  came in on. Through it a handler calls back (`new EventsSender(peer)`),
  reads `peer.id`, and keeps data on the connection in `peer.extensions`.
- **A sender replaces the client,** over anything that implements `Peer`: a
  `Connection`, or a handler's peer. A call with a deadline goes through
  `peer.call(…, { timeoutMs })` by hand: the generator doesn't read
  `@timeout_ms` yet.
- **`CONNECTION_IR_HASH`** covers every schema in the package. It also fixes
  each protocol's number (`ChatDispatcher.PROTOCOL`), its position among the
  package's protocols.

There's no `serveChat` helper: the connection serves. Protocols on
`datagram` or `jsonrpc` in the same package keep their `Client` and server.

## Both sides

```ts
import { Connection, JsonCodec } from "@comline/runtime";

// The side that accepts.
const server = await Connection.accept(transport, new JsonCodec(), CONNECTION_IR_HASH);
new ChatDispatcher(chatImpl).provideOn(server);

// The side that dials.
const client = await Connection.connect(transport, new JsonCodec(), CONNECTION_IR_HASH);
new EventsDispatcher(eventsImpl).provideOn(client);
const sent = await new ChatSender(client).send({ text: "hi" });

// The server calls the client on its own.
await new EventsSender(server).message({ text: "pushed" });
```

A connection starts reading as soon as it's made, and `closed` resolves when
the transport closes. Calls still waiting then reject with a `transport`
error. A request to a protocol this side doesn't provide is answered with a
fault.

## A handler calling back

```ts
class Sent {
  constructor(public count: bigint) {}
}

const chatImpl: Chat = {
  async send(peer, { text }) {
    await new EventsSender(peer).message({ text });
    const sent = peer.extensions.get(Sent) ?? new Sent(0n);
    sent.count++;
    peer.extensions.set(sent);
    return sent.count;
  },
  async count(peer) {
    return peer.extensions.get(Sent)?.count ?? 0n;
  },
};
```

`Extensions` holds one value per class. It belongs to the connection, so
`Sent` counts this client's messages and no one else's.

## Concurrency

- **Several calls can be in flight.** A reply goes to the call with its
  request id, so `Promise.all` over a sender's calls works. (On a lockstep
  `Client`, concurrent calls can take each other's replies.)
- **The peer's requests are handled one at a time, in order,** except while
  every running handler is waiting on a call to the peer. Then the next
  request starts, since it may be the nested call that handler needs.

## Without generated code

`conn.provide(protocol, dispatcher)` registers any `Dispatch`. One that
needs the peer implements the optional `dispatchWith(kind, params, reply,
peer)`. `Peer` has `codec`, `id`, `extensions`, `call(protocol, call, params,
{ timeoutMs })` and `notify`. `Datagram2Framing` is the framing; another
`ConnectionFraming` can be passed to `connect`, `accept` or
`Connection.unverified`.
