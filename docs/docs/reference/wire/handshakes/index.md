# Handshakes

What two ends exchange when a connection opens, before the first call:
`comline@2`, the default, which checks compatibility, and `comline@1`, which
checks identity.

`comline@2` is the default where all of a package's protocols are on
`datagram@3`, which is every package that takes the defaults. It runs one
handshake per connection, so a package whose protocols can't share one
(one on `jsonrpc`, `datagram@2` or a lockstep framing, say, or one naming
another handshake) gets `comline@1` for every protocol that names none, as
before. A package's `handshake` in `config.idp` overrides both. See
[Defaults before `comline@2`](#defaults-before-comline2) for what the change
of default means for a released package.

## Official handshakes

| Name | Does | Gives up |
| --- | --- | --- |
| `comline@2` (the default) | exchanges each version's facts, and decides by each protocol's line | nothing, unless `same_version_differs = warn`: then version honesty |
| `comline@1` | exchanges and checks schema, format and framing | nothing |
| `none` | sends and checks nothing | schema agreement and encoding agreement |

`none` is the absence of a handshake, so it is not declared anywhere.

## Usage resolution

A protocol's `@handshake` is picked first, then its package's `handshake` key in `config.idp`, then the official default
(`comline@2`, or `comline@1` in a package whose protocols can't all run `comline@2`):

```ids title="usage_resolution.ids"
@handshake = "com.acme.hello@1"
protocol Gateway { /* ... */ }
```

A handshake that takes [parameters](comline@2.md#parameters) is written as a dictionary
instead, its name under `name`, as `@framing` does. The plain name is shorthand
for a dictionary with only a name:

```ids
@handshake = { name = "comline@2", newer_consumer = refuse }
protocol Gateway { /* ... */ }
```

```title="config.idp"
handshake = { name = "comline@2" scope = "package" }
```

A protocol's own `@handshake` replaces the package's whole: the two aren't
merged.

## Defaults before `comline@2`

Until `comline@2` became the default, a protocol that named no handshake ran
`comline@1`, on `datagram@2`. A version built then is read as it was built:
its facts record the encodings it used, and one built before they were
recorded reads as `datagram@2` and `comline@1`, never as today's defaults.

So a package that takes the defaults shows a wire change on its first build
after the change: each protocol's framing and handshake change, its line
moves, and the next release takes a breaking bump (a minor one in 0.x). A
peer built from an older release refuses it, as it would any wire change.

To keep the old wire instead, state it in `config.idp`:

```idp
wire = { framing = "datagram@2" }
handshake = "comline@1"
```

A package that states them sees no change: not in its IR, its facts or its
version. Either can also be stated on its own, per protocol, with
`@framing` and `@handshake`.
