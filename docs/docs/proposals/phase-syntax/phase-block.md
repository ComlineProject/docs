# Proposal B — a `phase` block

Status: **under discussion** · See the [section overview](index.md) for the
question both answer

**The idea:** a new declaration states each phase's active protocols per
direction and its transitions, all in one place.

## Shape

```ids
phase Handshake {
    serverbound: [HandshakeServerbound]
    HandshakeServerbound.hello.next -> { Status, Login }
}

phase Login {
    serverbound: [LoginServerbound]
    clientbound: [LoginClientbound, KeepAliveClientbound]
    LoginServerbound.acknowledged -> Play
}

phase Play {
    serverbound: [Movement, Chat]
    clientbound: [World, Chat, KeepAliveClientbound]
}
```

## The case for it

- **One place shows everything about a phase:** its families in each direction,
  and where it leads. Reviewing a phase means reading one block.
- **No repetition on protocols,** and no defaults to trace.
- **Transitions are explicit and central,** so the whole state machine reads
  top to bottom.

## The case against

- **A new declaration kind:** grammar, the formatter, the language server,
  highlighting, the frozen IR, and its own rules in the version comparison.
- **The phase list isn't an ordinary enum,** so a client-chosen next phase
  needs its own form (`-> { Status, Login }`), and a field can't simply have the
  phase type unless phases also produce one.
- **It's a second table.** Ids stay on the functions, so the facts are again
  split between the protocols and the phase blocks, which is what generating
  the tables was meant to avoid.
- **The direction is restated.** `serverbound:` repeats what `@provider` already
  says about each protocol.

## When this would be the right call

If a phase's overview in the source matters more than reusing existing
constructs, and phases are reviewed as a state machine first.
