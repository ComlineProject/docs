# Proposal B — `@assumes`, per guarantee

Status: **rejected**: the same redundancy as [A](waives.md), and "assumes"
can read as a demand on the consumer · See the [section overview](index.md) for the
question all four answer

**The idea:** the marker states what the author **assumes** holds in place of
the check Comline would have made, one entry per guarantee, with the
justification. It's the same shape as [Proposal A](waives.md) with the
opposite emphasis: the claim the author makes, not what they give up.

## Shape

```ids
@handshake = "com.acme.legacy-hello@1"
@assumes(schema_agreement =
    "the 2009 gateway has no schema; its version is pinned by contract")
protocol Billing {
    function charge(order: Order) -> Receipt;
}
```

A consumer accepts each assumption by name:

```
dependencies = {
    acme::billing@2.1 = {
        accept_assumptions = ["Billing.schema_agreement"]
    }
}
```

## The case for it

- **The reason reads as a justification,** not an apology. It's the claim a
  consumer inherits: "schema agreement holds because the version is pinned by
  contract." That mirrors Rust's `// SAFETY:` comments, which say why an
  invariant holds, not that it's been dropped.
- **Established vocabulary.** *Assume–guarantee* reasoning is the standard
  framing for contracts between components in verification: a component
  assumes something of its environment in exchange for what it guarantees.
  Comline guarantees, and the author assumes.
- **It has A's precision:** per-guarantee acceptance, and core cross-checking
  the declared assumptions against what the handshake and encodings establish.

## The case against

- **The direction can be misread.** "This protocol assumes schema agreement"
  can read as a requirement placed *on the consumer* ("you must make sure the
  schemas agree"), not as the author's claim. Both readings are partly true,
  which is exactly the ambiguity the marker is meant to remove.
- **It under-signals.** An assumption sounds routine; nothing in the word says a
  guarantee is gone. Rust chose *unsafe* to alarm, and *assumes* doesn't.
- **Version honesty reads oddly.** `assumes(version_honesty = …)` on a breaking
  change released as minor says the opposite of what happened: the author is
  overriding the comparison, not assuming it's right.
- **New syntax,** the same work as A.

## When this would be the right call

If the reason is meant as a contract the consumer relies on. That favours
statements like "the version is pinned by contract", which a consumer can check,
over "we turned this off".
