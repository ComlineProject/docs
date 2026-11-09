# Granular `@unverified`

Status: **draft** · part of [A shared vocabulary](index.md) · revisits part
of [Marking a given-up guarantee](../guarantee-marker/index.md)

**The question.** `@unverified = "reason"` marks a whole protocol, with one
reason, and core works out which guarantees it gives up. Should the author
be able to name the guarantees, give each its own reason, and mark less than
a whole protocol?

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
   maximum". Marking that one argument would say where, and would leave the
   rest of the protocol verified.
3. **The schema text doesn't say what's given up.** This was accepted for C,
   on the grounds that tooling shows it. With a shared vocabulary the cost of
   writing it drops, and a reviewer reading a diff sees it without tooling.
4. **The author's acknowledgement is implicit.** The version comparison catches
   the set growing *between releases*. While a change is being developed, a
   marker written for one guarantee silently covers a second.

## Proposal

**Keep `@unverified = "reason"`, and allow a keyed form that names
guarantees, at the scope each guarantee has.** Core still computes the set,
and checks the author's form against it.

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

- **The plain form stays valid.** It acknowledges whatever core computes,
  exactly as today, so nothing existing breaks.
- **The keyed form names guarantees.** Each key is a guarantee from the
  vocabulary and each value is its reason. Core computes the set as today, and:
    - a computed guarantee the author didn't name is an **error** ("`Billing`
      also gives up `schema_agreement`: handshake `none`");
    - a named guarantee core doesn't find given up is a **warning**, like a
      needless marker today;
    - an unknown key is an **error**, with the vocabulary's spellings suggested.
- **Scopes come from the vocabulary.** Each guarantee lists where it can be
  marked. `schema_agreement`, `encoding_agreement` and `version_honesty` come
  from the handshake, so they apply to a protocol (or a package's defaults).
  `encoding_conformance` comes from the encodings, so a protocol.
  `bounded_size` comes from types, so a protocol, a function, an argument, a
  field or a type. Marking at the wrong scope is an error.
- **What's frozen** is each given-up guarantee with its scope (`Billing`,
  `Billing.upload(data)`) and its reason. Acceptances and the version
  comparison work on that, so narrowing a marker is visible and widening one
  is a major change.
- **Acceptance stays per protocol** (`accept_unverified = { Billing = [...] }`).
  A consumer accepts the protocol's whole set, inner scopes included. Whether
  acceptance should also name scopes is an open question below.

## Options considered

| | A. Today, plus narrower scopes | B. Plain or keyed (proposed) | C. Keyed only |
|---|---|---|---|
| Existing schemas | unchanged | unchanged | all must be rewritten |
| Says what's given up, in the text | no | when keyed | always |
| A reason per guarantee | no | yes | yes |
| Catches a second guarantee while developing | no | when keyed | yes |
| Grammar work | an annotation on arguments and fields | keyed annotation values (core#124), plus A's | same as B |
| Repeats what core computes | no | only where the author chooses | always, which was the objection to the earlier Proposal A |

**B** lets a package that wants precision have it, and costs nothing to a
package that doesn't. A `settings` switch (`annotations.unverified.keyed =
"required"`) could let a package or an organisation require the keyed form,
which gives C's guarantees where they're wanted.

## Depends on

- **The vocabulary**, for guarantee names, descriptions and scopes, so
  core, the language server, diagnostics and generated docs agree.
- **Keyed annotation values** (core#124). Today an annotation's value is a
  scalar, and a list is parsed as validator calls.
- **Annotations on arguments and fields.** `bounded_size` at argument scope
  needs a marker there. Check this against how bounds attach today (core#98).

## Open questions

- **Acceptance by scope:** should `accept_unverified` be able to accept
  `Billing.upload` alone, or is accepting the protocol's whole set enough?
- **Package-level defaults:** whether `config.idp` can carry a keyed marker for
  every protocol in the package (for example, a package-wide `handshake =
  "none"`).
- **Inheritance:** whether a function-scope marker covers every argument, and
  whether a type-scope marker covers every use of the type.
- **The word.** The keyed form is close to the earlier Proposal A
  (`@waives(…)`). Keeping `@unverified` for both forms means one marker to
  learn, and that is the assumption here.
