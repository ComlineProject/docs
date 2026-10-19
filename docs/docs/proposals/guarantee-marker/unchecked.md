# Proposal D — keep `@unchecked`

Status: **rejected**: "unchecked" says neither who doesn't check nor what,
and collides with validators "checking". [C](unverified.md) keeps its shape
under a clearer word · See the [section overview](index.md) for the
question all four answer

**The idea:** the first candidate, kept. A single marker with a reason, like
[Proposal C](unverified.md), named after the closest existing convention.

## Shape

```ids
@handshake = "com.acme.legacy-hello@1"
@unchecked = "the 2009 gateway has no schema; its version is pinned by contract"
protocol Billing {
    function charge(order: Order) -> Receipt;
}
```

The runtimes' call-site skip becomes `Client::new_unchecked`, following Rust's
`get_unchecked` / `from_utf8_unchecked` convention.

## The case for it

- **Familiar.** Rust (`*_unchecked` functions) and Swift (`@unchecked
  Sendable`) use the word for exactly this: the tool would normally verify
  something, and here the author vouches for it.
- **The runtime names come for free.** `Client::new_unchecked` reads naturally
  to any Rust developer.
- **Same simplicity as C:** a plain string annotation, no grammar work, and the
  affected guarantees inferred by core.

## The case against

- **"Unchecked by whom, and what?"** This is the objection that started the
  question. The word names neither the checker nor the guarantee.
- **It collides with Comline's other checks.** Comline already uses "check"
  for validation and the build:
  - validators "check" fields, and there's a `validator-checks-nothing`
    warning;
  - settings enforcement and diagnostics are build "checks".

  An `@unchecked` protocol can read as one whose fields aren't validated.
- **Java's `@SuppressWarnings("unchecked")`** means unchecked type casts, an
  unrelated sense many developers know.
- **Coarser acceptance,** as with C.

## When this would be the right call

If familiarity to Rust and Swift developers outweighs the ambiguity, and the
collision with validation can be avoided in the docs and diagnostics.
