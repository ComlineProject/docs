# Proposal C — `@unverified`, one marker

Status: **under discussion** · See the [section overview](index.md) for the
question all four answer

**The idea:** a single marker with a reason. Core works out which guarantees
are affected, from the handshake and encodings in use, and reports them. The
schema says *that* something isn't verified; core says *what*.

## Shape

```ids
@handshake = "com.acme.legacy-hello@1"
@unverified = "the 2009 gateway has no schema; its version is pinned by contract"
protocol Billing {
    function charge(order: Order) -> Receipt;
}
```

Core reports: *"`Billing` is unverified: schema agreement isn't established
(handshake `com.acme.legacy-hello@1`)"*. A consumer accepts the protocol:

```
dependencies = {
    acme::billing@2.1 = { accept_unverified = ["Billing"] }
}
```

## The case for it

- **It works with today's syntax.** It's a plain string annotation, gated with
  `annotations.unverified.allowed` like `@framing`. No grammar work.
- **Nothing to drift.** The affected guarantees are computed, not declared, so
  the schema can't claim a different set from the one actually given up.
- **One concept to learn,** and one marker per protocol however many guarantees
  are involved.
- **"Unverified" answers part of the objection.** It names the activity, which
  is verification, and the reader can see Comline is the one that would have
  verified.
- **Prior art:** Swift's `@unchecked Sendable` and Rust's `unsafe` are single
  markers. Rust pairs `unsafe` with a `// SAFETY:` comment, and this reason
  plays that role.

## The case against

- **The schema text doesn't say what's given up.** A reader has to rely on
  tooling (hover, build output) to learn which guarantee is affected.
- **Acceptance is coarser.** If a consumer accepts `Billing` as a whole, a
  dependency update that gives up a *second* guarantee on it passes silently.
  Recording the inferred set with the acceptance fixes that, but then the
  acceptance is per guarantee anyway, only hidden.
- **One reason covers everything.** A protocol giving up two guarantees for
  different reasons has to explain both in one string.
- **"Unverified by whom?"** is still a fair question for someone meeting it
  for the first time, if less so than for *unchecked*.

## When this would be the right call

If simplicity and today's syntax matter most, and the tooling (hover, build
output, generated docs) is trusted to show what the schema text doesn't.
