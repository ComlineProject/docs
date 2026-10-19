# Proposal A — an enum plus annotations

Status: **accepted** · with the points settled [below](#as-accepted) · See
the [section overview](index.md) for the question both answer

**The idea:** phases are an ordinary `enum`. Each protocol states the phase or
phases it's active in, and each transition packet states where it leads. The
generators produce the id and flow tables that are usually kept by hand.

## Shape

```ids
@phases
enum Phase {
    @initial
    Handshake
    Status
    Login
    Play
}

// The client may only choose Status or Login here.
validator HandshakeTarget for Phase {
    validate {
        assert(value == Phase.Status or value == Phase.Login,
               f"{value.name} can't be chosen at the handshake")
    }
}

@validators = [HandshakeTarget]
type NextPhase = Phase

@provider = Server
@phase = Handshake
protocol HandshakeServerbound {
    @id = 0x00
    @transition = next              // the client chooses: the field's own value
    function hello(protocol_version: u32, next: NextPhase);
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
    protocol.provider = Server
    protocol.phase = Login
}
```

## As accepted

Chosen over [the `phase` block](phase-block.md), with these points settled:

1. **Settings keys follow the existing path shape.** A default is
   `protocol.provider = Server`, beside gates like
   `protocol.annotations.framing.allowed`, with no `defaults.` group.
   - The settings group names (`annotations`, `validators`, `diagnostics`,
     `mode`) become reserved annotation names. Equally, a future settings
     group can't take an existing annotation's name.
   - **A default obeys the same gate as the annotation.** If `@framing` is
     forbidden, a `protocol.framing` default is forbidden too, so a default is
     never a way around a policy. (The package framing default in `config.idp`
     is a separate key, not gated.)
2. **The phase enum is marked with `@phases`,** an annotation, not a keyword.
   Phases need no new construct, and an annotation is typed and gated like the
   rest. There's one phase enum per connection's set of protocols; a second
   is an error naming both.
3. **The initial phase is marked with `@initial`** on its variant. It can't be
   the first variant: reordering enum variants is harmless under the
   [compatibility rules](../schema-compatibility.md), so order can't carry
   meaning. (`@default` would be ambiguous: an enum-typed field can have a
   default value.)
4. **A client-chosen target is limited by a validator,** on the field's type
   (an alias, since arguments carry no annotations), with two rules:
   - **On a field that decides a transition, validators always run,**
     whatever `validate_on_decode` says. Otherwise a client could skip
     straight to `Play`.
   - **The validator's condition must reduce to a set of variants**
     (`value == Phase.Status or value == Phase.Login`). Core extracts that set
     for the state machine and its docs. A condition it can't reduce is an
     error.

   This needs validators to accept enum targets and compare against enum
   variants, which they don't yet. Reusing validators keeps the restriction
   visible to consumers and under the usual versioning rules (narrowing is
   major).
5. **Enums on a packet wire need explicit numeric values.** A phase field is a
   varint `1`, `2` or `3` in Minecraft's handshake, while Comline enums travel
   by name. Enum variant values and union tags
   ([core#126](https://github.com/ComlineProject/core/issues/126)) should be one
   mechanism.
6. **Id uniqueness depends on the framing.** With a family field in the header,
   (family, id) is unique per phase and direction. Without one (flat tables),
   ids are unique across every family active in that phase and direction. So
   the framing's [profile](../schema-compatibility.md#encoding-profiles) states
   whether the header carries a family, and core checks against it.

Annotations on enums and on enum variants (`@phases`, `@initial`) aren't
allowed by the grammar yet; they need adding.

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
