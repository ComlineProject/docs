# Proposal A — `@waives`, per guarantee

Status: **rejected**: core can always work out which guarantees are given up,
so naming them repeats what it computes, at the cost of new syntax. The
per-guarantee acceptance it offered is kept in [C](unverified.md#as-accepted) · See the [section overview](index.md) for the
question all four answer

**The idea:** the marker names each guarantee the author gives up, with a reason
for each. To *waive* is to knowingly give up something one is entitled to.

## Shape

```ids
@handshake = "com.acme.legacy-hello@1"
@waives(schema_agreement =
    "the 2009 gateway has no schema; its version is pinned by contract")
protocol Billing {
    function charge(order: Order) -> Receipt;
}
```

A consumer accepts each waiver by name:

```
dependencies = {
    acme::billing@2.1 = {
        accept_waivers = ["Billing.schema_agreement"]
    }
}
```

The package-level cases read the same way in `config.idp`:

```
waives = { version_honesty = "a field rename the gateway ignores" }
```

Diagnostics follow suit: *"`Billing` waives schema agreement: the 2009 gateway
has no schema"*, and *"`Billing`'s handshake doesn't establish encoding agreement
either; waive it too, or use a handshake that does"*.

## The case for it

- **It answers both halves of the objection.** *What* is in the schema. *Who* is
  in the verb: the author waives.
- **Per-guarantee acceptance falls out naturally.** A dependency update that
  starts waiving a second guarantee on a protocol a consumer already accepted is
  a new waiver, so it needs a new acceptance.
- **Core can cross-check.** The handshake's profile says what it establishes,
  so core knows what is actually given up:
  - a waiver missing for a guarantee that isn't established is an error;
  - a waiver for one that is established is a warning.
  - The declaration can't silently drift from reality.
- **Every case reads the same.** Handshakes, unproven encodings and
  version-rule overrides all say "waives *guarantee*: *reason*", in the schema
  and in `config.idp` alike.
- **Prior art for the consumer side:** Kotlin's `@RequiresOptIn` / `@OptIn`. A
  declaration names a specific concern, and each consumer opts into that
  concern, not into "unsafe things" in general.

## The case against

- **"Waive" is a legal word.** It's precise, but less familiar to developers
  than *unsafe* or *unchecked*.
- **Strictly, one waives one's own right.** Here the author gives up a guarantee
  that would have protected the *consumer*. The consumer's acceptance repairs
  that: both sides sign. But the word alone suggests the author is giving up
  something of their own.
- **New syntax.** Keyed annotation values don't exist yet, and a list
  annotation is parsed as validator calls today. Core grammar work is needed.
- **More to write** than a single string, especially for a protocol that gives
  up two guarantees at once.
- **The call-site skip is awkward to name after it.** `Client::new_waiving_…`
  reads poorly, so the runtimes would likely use a descriptive name such as
  `Client::without_handshake`.

## When this would be the right call

If precision for consumers matters most: a waiver is specific, can be accepted
per guarantee, and core can check it against what's actually given up.
