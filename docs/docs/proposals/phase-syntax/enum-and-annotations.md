# Proposal A — an enum plus annotations

Status: **under discussion** · See the [section overview](index.md) for the
question both answer

**The idea:** phases are an ordinary `enum`. Each protocol states the phase or
phases it's active in, and each transition packet states where it leads. The
generators produce the id and flow tables that are usually kept by hand.

## Shape

```ids
enum Phase { Handshake, Status, Login, Play }

@provider = Server
@phase = Handshake
protocol HandshakeServerbound {
    @id = 0x00
    @transition = next              // the client chooses: the field's own value
    function hello(protocol_version: u32, next: Phase);
}

@provider = Server
@phase = Login
protocol LoginServerbound {
    @id = 0x00
    function start(name: string);

    @id = 0x03
    @transition = Play              // the client's acknowledgement
    function acknowledged();
}

@provider = Client
@phase = [Login, Play]              // active in both
protocol KeepAliveClientbound {
    @id = 0x26
    function keep_alive(id: u64);
}
```

With [settings defaults](https://github.com/ComlineProject/core/issues/125),
a schema file per side or per phase states the shared values once:

```ids
// login_server.ids
settings {
    defaults.protocol.provider = Server
    defaults.protocol.phase = Login
}
```

## The case for it

- **It's how phases are usually described:** an enum, without a new construct
  to learn.
- **No separate tables to keep in step.** Ids, active phases, transitions and
  replies (`@reply` / `@match`) sit on the declarations they belong to, and
  the dispatch and flow tables are generated.
- **A client-chosen next phase falls out naturally.** `Phase` is a real enum, so
  a packet field can have that type, and `@transition = next` means whatever
  the client sent. Minecraft's handshake needs no special syntax.
- **Repetition stays low.** Settings defaults and named presets carry
  `@provider` and `@phase` for a whole file. A declaration overrides only
  what differs.
- **One file per phase gives the overview.** The file itself lists the phase's
  families.

## The case against

- **Membership is spread out** unless the schema is laid out per phase. When
  it isn't, tooling has to supply the overview: hover, generated docs, a
  per-phase table view.
- **It needs typed annotation values**
  ([core#124](https://github.com/ComlineProject/core/issues/124)) for
  `@phase = [Login, Play]` and for references like `@transition = next`.
  Annotation lists are parsed as validator calls today.
- **Defaults are indirect.** A protocol's phase may come from a settings block
  elsewhere in the file, and hover has to show where.

## When this would be the right call

If phases should read the way they're usually written, and the language's
existing pieces (enums, annotations, settings) should carry them with no new
construct.
