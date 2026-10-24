# Package wire defaults

Status: **under discussion** · decided with the author 2026-10-25, open for
review before any code · issues:
[core#139](https://github.com/ComlineProject/core/issues/139),
[runtime#26](https://github.com/ComlineProject/runtime/issues/26),
[generation#82](https://github.com/ComlineProject/generation/issues/82),
[cli#100](https://github.com/ComlineProject/cli/issues/100),
[simulator#25](https://github.com/ComlineProject/simulator/issues/25)

**The question:** what a package gets on the wire when it says nothing, and how
little code it takes to serve every protocol it has.

Four changes, made together because each leans on the others:

1. A package declares its framing and wire format in `config.idp`, under a
   `wire` key.
2. The built-in framing becomes `datagram@2`, so every protocol runs on a
   connection unless it opts out.
3. A new wire format, `packed@1`, becomes the built-in format: fixed-width
   fields with no tags and no names, like a packed C struct.
4. Generated code gets a `Services` struct and a package-level `serve`, so
   serving every protocol is one call.

## The problem

A server that provides three protocols today looks like this:

```rust
pub fn serve_one(listener: TcpListener, state: SharedAppState) -> Result<(), RuntimeError> {
    let (stream, _) = listener.accept().map_err(|_| RuntimeError::Transport)?;
    let mut transport = Tcp::new(stream);

    AccountProtocolDispatcher(AccountServiceImpl { state: state.clone() })
        .serve(&mut transport, MsgPack)?;
    PlayerProtocolDispatcher(PlayerServiceImpl { state: state.clone() })
        .serve(&mut transport, MsgPack)?;
    CharacterInventoryProtocolDispatcher(CharacterInventoryImpl { state: state.clone() })
        .serve(&mut transport, MsgPack)?;
    Ok(())
}
```

It has three problems:

- **It doesn't serve all three.** Each `serve` runs until the peer
  disconnects. The default framing, `datagram` (`@1`), names only the call in a
  request, not the protocol, so one transport can carry only one protocol.
  `Account` gets the whole connection; `Player` then runs a handshake on a
  closed stream and fails.
- **The format is repeated at every call,** although both peers must agree on
  it: its name is part of the handshake. It belongs to the package, not to each
  call site.
- **Forgetting a protocol compiles.** Nothing ties the set of dispatchers
  passed in to the set of protocols the package provides.

Connections (`datagram@2`, see [Connections](connections.md)) already carry a
protocol number in each frame and let one transport serve many protocols. But a
package only gets one by writing `@framing = "datagram@2"`, which settings
forbid by default, or `default_framing` in `comline.toml`, which belongs to
whoever generates the code rather than to the package.

## 1. The `wire` key

```text
congregation game
specification_version = 1

wire = {
    format = "packed@1"
    framing = "datagram@2"
}
```

- Both entries are optional, and quoted (the manifest grammar takes a bare
  `msgpack@1` as a key, not a value).
- **`format`**: `packed@1` (the default), `json@1` or `msgpack@1`. The names are
  the ones the runtimes already put in the handshake.
- **`framing`**: any `@framing` spelling, canonicalised the same way.
  `datagram@1` becomes an accepted spelling of today's `datagram`.
- **Resolution, most specific first:**
  - framing: the protocol's own `@framing`, then `wire.framing`, then
    `datagram@2`;
  - format: `wire.format`, then `packed@1`.
- Core writes the resolved framing into each protocol's compiled IR, the way
  the package `handshake` key already works. Generators and the playground then
  read one place, and the package default isn't subject to the settings gate
  on `@framing`.
- The format isn't part of the schema IR. Core keeps it in the package config
  and the generation request carries it to the generators.
- **`default_framing` leaves `comline.toml`.** It becomes an error naming the
  `wire` key, as [Schema compatibility](schema-compatibility.md) already
  planned: the framing is part of the contract both peers build from, so the
  producer decides it.
- Changing either entry is a **major** change: old and new peers no longer
  understand each other.

This is a narrower form of the declaration in
[Schema compatibility](schema-compatibility.md) (one default per kind rather
than a list of everything the package speaks). A list can still be added later
alongside the default.

## 2. `datagram@2` by default

A protocol with no `@framing` and no `wire.framing` runs on a connection.

- **Several protocols share one transport**, each frame naming its protocol.
- **Reverse calls work without opting in.** `@provider = Client` no longer
  needs `@framing = "datagram@2"` next to it.
- **`async = true` takes effect** on a plain package, since it applies to
  connection protocols.
- **To keep the old wire**, write `wire = { framing = "datagram@1" }` or
  `@framing = "datagram@1"` on one protocol.

**Compatibility.** Every package with a protocol and no declared framing
changes its wire: the frames gain a protocol number and the handshake hash
becomes the package's. Old and new peers can't talk. Comline is before 1.0, so
the default changes now rather than with a new `specification_version` edition.
This amends [Schema compatibility](schema-compatibility.md), which planned the
change only for a new edition.

## 3. `packed@1`

The goal is the smallest, fastest encoding that still decodes safely: the
schema already says every field's type and width, so the bytes don't repeat
it.

### Layout

A value is its fields back to back, in declaration order, with no padding,
headers, names or type tags.

| Type | Bytes |
|---|---|
| `bool` | 1 byte: `00` or `01`; anything else is an error |
| `u8` `u16` `u32` `u64` | 1, 2, 4, 8 bytes, little-endian |
| `s8` `s16` `s32` `s64` | 1, 2, 4, 8 bytes, little-endian two's complement |
| `f32` `f64` | 4, 8 bytes, IEEE 754 little-endian |
| `string` | length as a varint, then that many bytes of UTF-8 (invalid UTF-8 is an error) |
| `T[]` | element count as a varint, then the elements |
| `T[N]` | the N elements; the length is in the schema |
| struct, error body, a call's arguments | the fields in declaration order |
| optional field | `00`, or `01` followed by the value |
| enum | the variant's index in declaration order, as a varint |
| `union(A B ...)` | the member's index in the union, as a varint, then its value (no generator supports unions yet; this fixes their layout ahead of time) |
| `()` | nothing |

**Varints** are unsigned LEB128: 7 bits per byte, low bits first, high bit set
on every byte but the last. Only the shortest encoding is accepted (an overlong
one is an error), so a value has exactly one encoding.

**Decoding is strict.** A value must use all the bytes it was given: trailing
bytes are an error. A length larger than the bytes left is an error before
anything is allocated, so a hostile length can't make the decoder reserve
memory.

### Example

```text
enum Class { Warrior, Mage }

struct Player {
    id: u32
    hp: u16
    name: string
    optional guild: string
    class: Class
    pos: f32[2]
}
```

`Player { id: 7, hp: 100, name: "ab", guild: none, class: Mage, pos: [1.0, 2.0] }`:

```text
07 00 00 00   id
64 00         hp
02 61 62      name: length 2, "ab"
00            guild: absent
01            class: Mage, index 1
00 00 80 3f   pos[0] = 1.0
00 00 00 40   pos[1] = 2.0
```

That's 19 bytes. The same value in `json@1` is 73.

### Why fixed widths

- **Speed**: each fixed field is a copy, with no branching per byte.
- **Size**: it comes from the widths the schema chose. A `u64` always takes 8
  bytes, even holding `1`. A field that's usually small should be declared
  narrow.
- **Varints only where the schema can't say the size**: lengths, counts and
  enum and union indexes. These are almost always small, so they usually take
  one byte.

### Evolution

`packed@1` is positional, like `msgpack@1`:

- **Major:** adding, removing or reordering fields (an optional one included),
  or reordering enum variants or union members.
- **Minor:** appending an enum variant. An old peer can't decode the new one,
  so don't send it to one (the same caveat as for every format).

[Schema compatibility](schema-compatibility.md)'s rules table gains a
`packed@1` column, matching `msgpack@1`'s.

### In the runtimes

- **Rust**: `comline_runtime::format::Packed`, a `WireFormat` built as a serde
  serializer and deserializer.
  - It needs `alloc` but not `std`, so it works on targets the `std`-only JSON
    and MessagePack formats don't.
  - It never needs `deserialize_any`, and the generated types already avoid the
    serde features a positional format can't support (`flatten`, untagged
    enums, skipped fields).
- **TypeScript** is the larger piece. A JS value doesn't say whether a number
  is a `u16` or an `f64`, so the decoder needs the schema.
  - The generator emits a shape for each type (field order, widths, element
    types), and `PackedCodec` walks it.
  - `u64` and `s64` stay `bigint`, as in the JSON codec.
- **Conformance vectors** pin the bytes for each type and each decoding error.
  Both runtimes run them, as they do for the existing formats.

## 4. `Services` and `serve`

The generator knows which protocols the package provides and on which side, so
it emits the setup code.

The example above becomes:

```rust
pub fn serve_one(listener: TcpListener, state: SharedAppState) -> Result<(), RuntimeError> {
    let (stream, _) = listener.accept().map_err(|_| RuntimeError::Transport)?;
    game::serve(Tcp::new(stream), game::Services {
        account: AccountServiceImpl { state: state.clone() },
        player: PlayerServiceImpl { state: state.clone() },
        character_inventory: CharacterInventoryImpl { state },
    })
}
```

### What's generated, once per package

In `lib` mode it goes in `src/lib.rs`; in `code` mode, in a `connection.rs`
beside the schema files.

- **`pub type Format`**: the declared format's runtime type
  (`comline_runtime::format::Packed` by default).
- **`CONNECTION_IR_HASH`**, which moves here from the schema files (they
  re-export it).
- **`Services`**: one field for each protocol the accepting side provides
  (`@provider = Server`, the default, and `Multiple`).
  - Each field's type is generic over that protocol's trait.
  - A missing field is a compile error, so a protocol can't be forgotten.
  - Fields are the protocol's name in snake case, prefixed with its namespace
    only where two names clash.
- **`ClientServices`**: the same for the dialling side (`Client` and
  `Multiple`). It's omitted when there are none.
- **Functions:**

  | Function | Does |
  |---|---|
  | `serve(transport, Services)` | accept, run the handshake, provide every protocol, serve until the peer leaves |
  | `accept(transport, Services)` | the same, but return the connection, so the caller can call back or serve one request at a time |
  | `connect(transport, ClientServices)` | dial, run the handshake, provide the client-side protocols, return the connection |

  `connect` takes no services argument when there are no client-side
  protocols. Calls to the server go through the existing senders:
  `AccountSender(&mut conn).login(..)`.
- **Async** (`async = true`) gives the same three functions over
  `AsyncConnection`:
  - `accept` returns the connection unstarted, so the caller can take its
    `handle()` before running it;
  - `serve` awaits `run()`.
- **The framing and handshake** follow the package: JSON-RPC connections use
  `JsonRpcFraming`, and `@handshake = "none"` skips the handshake. If the
  connection protocols disagree on either, there is no single connection to
  set up, so these helpers aren't generated and `comline generate` warns why.

### Per-protocol helpers

A protocol that opts out of connections keeps its own `serve` and `connect`.

- Their `format` argument goes away: they use `Format`.
- `serve_with_format` and `connect_with_format` keep the generic form for a
  caller that needs another format.

### TypeScript

TypeScript gets the same shape:
- `Services` as an interface;
- `serve(transport, { account, player, characterInventory })`;
- `connect(transport, clientServices)`;
- `export const Format`.

## What changes for an existing package

| Package | Before | After |
|---|---|---|
| No `@framing`, no `default_framing` | `datagram@1`, one protocol per transport, format chosen per call | `datagram@2` and `packed@1`; regenerate both peers |
| `default_framing = "datagram@2"` in `comline.toml` | connections | the same, once the setting moves to `wire.framing` |
| `@framing = "jsonrpc"` | JSON-RPC, as before | as before; the format default doesn't apply to JSON-RPC, which is JSON by definition |
| Calls `XDispatcher(..).serve(&mut t, MsgPack)` | compiles | the protocol is now on a connection: use `serve(t, Services { .. })`, or keep the old wire with `wire = { framing = "datagram@1", format = "msgpack@1" }` |

## What it touches

In the order it would be built:

1. **runtime**: `packed@1` in Rust and TypeScript, with conformance vectors.
2. **core**:
   - the `wire` key and its config IR;
   - writing the resolved framing into each protocol;
   - `datagram@2` as the default;
   - the reverse-call check no longer requiring an explicit framing;
   - config diffs for `wire`.
3. **generation**: the format in the generation request, `default_framing`
   removed, and the conformance goldens re-blessed (plain protocols become
   connection protocols).
4. **comline-rust** and **comline-typescript**: `Format`, `Services`, the
   package functions, and TypeScript's packed shapes.
5. **cli**:
   - `default_framing` becomes an error;
   - the format reaches the generators;
   - `comline new` writes a commented `wire` entry.
6. **simulator** and **playground**: `datagram@2` frames, the resolved framing
   read from the IR, and `packed@1` among the formats.
7. **language server**, **VS Code extension** and the **docs**.

## Open questions

- **JSON-RPC and `wire.format`.** JSON-RPC carries JSON, so a `wire.format`
  other than `json@1` has no effect on a JSON-RPC protocol. Should declaring
  both be an error, or should the format apply only to the package's
  non-JSON-RPC protocols (the proposal's reading)?
- **A `u64` that is usually small.** Fixed widths make it 8 bytes. Is it
  worth a later `varint` field annotation, or is "declare it narrower" enough?
