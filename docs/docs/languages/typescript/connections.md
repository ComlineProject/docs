# Connections

Every protocol runs on a
[connection](../../guide/idl/protocol.md#calls-in-both-directions) unless it
picks the lockstep `datagram` framing, in which case it gets a
[client and server](client-and-server.md) instead. This page uses this
schema:

```ids
protocol Chat {
    function send(text: string) -> u64;
    function count() -> u64;
}

@provider = Client
protocol Events {
    function message(text: string) -> bool;
    function ping();
}
```

## Serving every protocol

The package gets one `serve`, taking a `Services` object with a field per
protocol the server provides. Leaving one out doesn't type-check:

```ts
import { connect, serve, chat } from "my-package";

// The side that accepts: handshake, provide every protocol, serve until
// the peer leaves.
await serve(transport, { chat: chatImpl });

// The side that dials: handshake, provide the client's protocols, and call
// the server's through their senders.
const conn = await connect(transport, { events: eventsImpl });
const sent = await new chat.ChatSender(conn).send({ text: "hi" });
```

- **`accept(transport, services)`** returns the connection, already serving,
  so the server can call the client through it.
- **`ClientServices`** holds the protocols the dialling side provides
  (`@provider = Client` or `Multiple`). With none, `connect` takes only the
  transport.
- **Field names** are the protocol's name in camelCase
  (`CharacterInventory` is `characterInventory`), prefixed with the namespace
  where two schemas declare a protocol of the same name.
- **The format** is the package's `Format`
  ([Framing & wire format](framing-and-wire-format.md)); the framing and
  handshake are the protocols'. When the protocols on connections disagree on
  either, no one connection carries them all, so these functions aren't
  generated and `comline generate` warns why.

They're in `connection.ts`, which a `lib`-mode package's `index.ts`
re-exports.

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

// Once per package, in connection.ts:
export const Format: Codec = new PackedCodec();
export const CONNECTION_IR_HASH = 0x…n;  // checked by the handshake
export interface Services { chat: Chat }
export interface ClientServices { events: Events }
export async function accept(…); serve(…); connect(…);
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

There's no `serveChat` helper: the package's `serve` serves them all. Protocols on
`datagram` in the same package keep their `Client` and server, and so do
`jsonrpc` ones unless the package has a JSON-RPC protocol on a connection (see
[Over JSON-RPC](#over-json-rpc)).

## By hand

The package's functions are a few lines over the runtime's `Connection`,
which is also how to pick another codec for one connection:

```ts
import { Connection } from "@comline/runtime";

// The side that accepts.
const server = await Connection.accept(transport, Format, CONNECTION_IR_HASH);
new ChatDispatcher(chatImpl).provideOn(server);

// The side that dials.
const client = await Connection.connect(transport, Format, CONNECTION_IR_HASH);
new EventsDispatcher(eventsImpl).provideOn(client);
const sent = await new ChatSender(client).send({ text: "hi" });

// The server calls the client on its own.
await new EventsSender(server).message({ text: "pushed" });
```

A connection starts reading as soon as it's made, and `closed` resolves when
the transport closes. Calls still waiting then reject with a `transport`
error. A request to a protocol this side doesn't provide is answered with a
fault.

## Over JSON-RPC

A JSON-RPC protocol the client provides runs on a connection too, and then so
do the package's other JSON-RPC protocols
([the rules](../../guide/idl/protocol.md#json-rpc-on-a-connection)). Pass
`JsonRpcConnectionFraming` to both ends (the package's `serve` and `connect`
do); the rest of this page is unchanged:

```ts
import { Connection, JsonCodec, JsonRpcConnectionFraming } from "@comline/runtime";

const server = await Connection.accept(transport, new JsonCodec(), CONNECTION_IR_HASH, new JsonRpcConnectionFraming());
const client = await Connection.connect(transport, new JsonCodec(), CONNECTION_IR_HASH, new JsonRpcConnectionFraming());
```

- **Each call table holds method names:** `["send", "count"]`, or under
  `method_names = qualified`, `["chat.Events/message", "chat.Events/ping"]`.
  A request is routed to the provided protocol whose table has its method.
- **A one-way call is a notification,** sent with no `id`. A request without
  one gets no reply, even if its function returns a value.

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
{ timeoutMs })` and `notify`. `Datagram2Framing` is the default framing; another
`ConnectionFraming`, such as `JsonRpcConnectionFraming`, can be passed to
`connect`, `accept` or `Connection.unverified`.
