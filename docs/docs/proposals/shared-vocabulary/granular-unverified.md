# Granular `@unverified`

Status: **accepted** · decided 2026-11-12 · tracked in [core#219](https://github.com/ComlineProject/core/issues/219) and
[core#222](https://github.com/ComlineProject/core/issues/222) · part of [A shared vocabulary](index.md) · revisits part
of [Marking a given-up guarantee](../guarantee-marker/index.md)

**The question.** `@unverified = "reason"` marks a whole protocol, with one
reason, and core works out which guarantees it gives up. Should the author
be able to name the guarantees, give each its own reason, and mark less than
a whole protocol, without making it any easier to lose a guarantee unnoticed?

**Decided: yes,** as an optional keyed form beside the plain one, under the
rules below.

## What was decided, and what it already covers

[Proposal C](../guarantee-marker/unverified.md) was chosen over naming the
guarantees ([A](../guarantee-marker/waives.md), [B](../guarantee-marker/assumes.md)),
because naming them "would only repeat" what core computes. Two refinements
closed most of the risk:

- a consumer's `accept_unverified` records the **set** core worked out, so a
  dependency that gives up one more guarantee needs a new acceptance;
- the set is **frozen** into the compiled schema, so the author's own version
  comparison reports it growing as a major change.

Those stay. This proposal doesn't reopen *whether* core computes the set.

## What it doesn't cover

1. **One reason for everything.** A protocol that gives up
   `encoding_conformance` (a framing without vectors) and `bounded_size` (an
   unbounded `bytes` argument) explains both in one string. Generated docs and
   hover text can't say which reason belongs to which guarantee, and for a
   third-party encoding they can't name the cause at all (generation#93).
2. **The scope is always the protocol.** `bounded_size` comes from a type: one
   unbounded argument anywhere a protocol reaches marks the whole protocol,
   and the diagnostic says only "a string, list or nesting it reaches has no
   maximum".
3. **The schema text doesn't say what's given up.** This was accepted for C,
   on the grounds that tooling shows it. With a shared vocabulary, writing it
   costs little, and a reviewer reading a diff sees it without tooling.
4. **The author's acknowledgement is implicit.** The version comparison catches
   the set growing *between releases*. While a change is being developed, a
   marker written for one guarantee silently covers a second.
5. **Chains across packages aren't explicit.** When package A's type gives up a
   guarantee, B uses it, and C uses B, nothing requires B and C to see A's
   cause and acknowledge it themselves.

## The safety invariant

Everything below serves one rule, which has to hold with no exceptions:

> **If a package compiles, every guarantee given up anywhere a protocol
> reaches, through any chain of types and packages, has been acknowledged in
> that package and accepted by every consumer of that protocol. Every
> acknowledgement and acceptance is pinned to the exact causes it covered,
> so any change upstream asks again.**

## Proposal

### Two forms, at any scope

`@unverified = "reason"` stays valid. An optional keyed form names
guarantees. Both can be written at any scope a given-up guarantee allows:

```ids
@framing = "com.acme.f@1"
@unverified(encoding_conformance = "com.acme.f@1 ships no vectors yet")
protocol Billing {
    function charge(order: Order) -> Receipt;

    function upload(
        @unverified(bounded_size = "legacy gateway blob, sized by the gateway")
        data: bytes
    );
}
```

- **Plain:** acknowledges whatever core computes at that scope, as today.
- **Keyed:** each key is a guarantee from the vocabulary, each value its
  reason. Against what core computes:
    - a computed guarantee that isn't named is an **error**;
    - a named guarantee that isn't given up is a **warning**, like a needless
      marker today;
    - an unknown key is an **error**, with spellings suggested from the vocabulary.

### Scopes come from each guarantee

A guarantee's scopes follow from where its cause sits, and are stated in its
catalog entry (`catalog/guarantees.cue` in the specification), outermost to
innermost. A new guarantee declares its own scopes, and core needs no special
case for it.

| Guarantee | Comes from | Scopes |
|---|---|---|
| `schema_agreement`, `encoding_agreement` | the handshake | package, protocol |
| `version_honesty` | `comline@2` policies | package, protocol |
| `encoding_conformance` | the format and framing | package, protocol |
| `bounded_size` | types | protocol, function, argument, field, type |

A marker at a scope its guarantee doesn't allow is an error.

### Coverage: outer covers inner, strict on request

**Decided:** by default a marker covers causes inside it: a protocol-level `bounded_size`
covers one unbounded argument, exactly as today, so nothing existing breaks.
Tooling suggests the narrower placement.

A package can opt into **strict** (`annotations.unverified.strict = true`; this
is the settings switch that requires the keyed form). The keyed form is then
required, and each marker must sit at the innermost scope
where its cause is. That suits packages that want every given-up guarantee
named where it happens.

### Chains: once per package, never inherited

Computing stays transitive, and **a marker never subtracts** from it. Core
walks every type a protocol reaches, into dependencies' frozen IR, and finds
every cause. A marker only acknowledges.

Acknowledgement is **per package, never inherited:**

```text
A::Blob = bytes              A marks it:  @unverified(bounded_size = "legacy gateway")
B::Upload { data: A::Blob }  B must acknowledge it (on Upload, the field, or a protocol reaching it)
C::Order  { blob: B::Upload } C must acknowledge it too
```

- Each package whose types or protocols reach a cause acknowledges it **once**,
  anywhere on the path inside that package. Within one package the author
  already sees the path; every package boundary asks again.
- A's reason travels along as the **origin**, and is shown at every hop, but
  A's marker satisfies only A.
- Diagnostics, `inspect`, hover and generated docs show the whole chain:
  *"`C::Orders` gives up `bounded_size`: `C::Order.blob` → `B::Upload.data` →
  `A::Blob` (`bytes` without a maximum). A's reason: 'legacy gateway'."*

### Pinned to the causes

An acknowledgement, and a consumer's acceptance, records what it covered: each
guarantee with the **chain to each cause**. If A adds a second unbounded field,
or B swaps `A::Blob` for another unverified type, the record no longer
matches, and B, C and every consumer get an error until they acknowledge
again. A guarantee can't be lost by reuse, however many packages it passes
through.

What's frozen is therefore (guarantee, scope path, chain to the cause,
reason). Narrowing a marker is not a major change, since nothing more is
given up. Widening one, or adding a cause, is. The frozen shape changes, so
this is **IR format 4**.

### Package-default causes: acknowledged next to the cause

A package setting can give a guarantee up for every protocol that inherits
it, for example `handshake = "none"` in `config.idp`. Its acknowledgement sits
beside that setting:

```text
handshake = "none"
unverified = { schema_agreement = "the gateway pins schemas by contract",
               encoding_agreement = "the gateway pins schemas by contract" }
```

- It covers **only the causes that come from that setting**, and only for the
  protocols that inherit it. A protocol with its own handshake isn't
  covered, and neither is any other cause (an unbounded type, a framing
  without vectors).
- Each covered protocol's frozen record says it was acknowledged at package
  scope, with the reason.
- It is pinned like any other marker: if the setting changes, it no longer
  matches and the build asks again.
- A blanket package marker covering everything in a package is ruled out.
  That is exactly the gap this proposal closes.

### Acceptance stays per protocol

`accept_unverified = { Billing = [...] }` accepts the protocol's whole frozen
set, inner scopes and chains included. It is pinned like an acknowledgement,
so a new inner cause still asks for re-acceptance. Acceptance by narrower
scope is not adopted: a consumer accepts a protocol as a whole.

### A newer spec that finds an existing loss

The spec can add a guarantee (say, a future "transport fit"), and an existing
protocol may turn out to give it up although its schema didn't change.

- **Safety:** markers and acceptances are pinned to a set that no longer
  matches, so the author and every consumer are asked again. Nothing passes
  silently.
- **Version honesty:** `diff` recomputes both versions under the newer spec
  before comparing, so the version comparison doesn't report a major change
  the author didn't make. The frozen IR keeps the types and parameters this
  needs.

### Fail closed

If the build can't see a dependency's declarations or IR, it counts the
guarantee as given up and refuses. An editor's incomplete view can show a
warning instead, but a build never judges with less than the full picture.
Any path that does is a safety bug. Known today: `compat` and `diff` don't see
a dependency's encoding declarations (core#206).

## Testing the invariant

Today there are unit tests (`core/tests/package/unverified.rs`), fuzz targets
for parsing and compiling robustness, and runtime vectors proving that decoders
refuse values over a bound. Nothing tests the invariant across package graphs.
This proposal adds these, tracked as core#223, core#224 and core#225:

1. **A property test with an independent oracle,** in core. It generates
   random package graphs (bounded and unbounded types, chains across
   packages, markers at random scopes, acceptances, upstream changes) and checks
   that *the build succeeds exactly when the oracle says every hop acknowledged
   and every consumer accepted*. It's the same differential idea as the
   runtime's `ffi_vs_core`.
2. **A fuzz target** running the same check over arbitrary graphs, in core's
   nightly fuzz CI.
3. **Compiler conformance cases** in the spec repository: schema graphs with
   their expected given-up sets, chains and errors, as data. Any compiler, the
   language server or another tool must reproduce them, the way runtimes must
   reproduce bytes today.
4. **An audit** of every place that judges guarantees (the validator,
   `compat`, `diff`, `inspect`, the language server) for any path that can see
   less than the full picture.

## Options considered

| | A. Today, plus narrower scopes (*rejected*) | B. Plain or keyed (**chosen**) | C. Keyed only (*rejected*) |
|---|---|---|---|
| Existing schemas | unchanged | unchanged | all must be rewritten |
| Says what's given up, in the text | no | when keyed, always under strict | always |
| A reason per guarantee | no | yes | yes |
| Catches a second guarantee while developing | no | when keyed, and always under strict | yes |
| Repeats what core computes | no | only where the author chooses | always, which was the objection to the earlier Proposal A |

## Depends on

- **The vocabulary**, for guarantee names, descriptions and scopes.
- **Keyed annotation values** (core#124), not built yet. Today an annotation's value is a
  scalar, and a list is parsed as validator calls.
- **Markers on arguments and fields.** Check this against how bounds attach
  today (core#98).

## The word

**Decided:** `@unverified` for both forms. The objection to the earlier `@waives(…)` was to
naming guarantees at all, not to the word. Now that naming is optional and
checked, the choice is about readability. `@unverified(bounded_size = "…")`
reads accurately: Comline doesn't verify it. And one word already runs through
the annotation, `accept_unverified`, `annotations.unverified` and the
`unverified::*` diagnostic codes.
