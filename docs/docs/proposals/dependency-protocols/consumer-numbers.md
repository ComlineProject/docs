# Proposal B — the consumer numbers its dependencies' protocols

Status: **rejected** (2026-11-14) as a default, see [verdict](#verdict); an
explicit opt-in re-export may come back ·
See the [section overview](index.md) for the question all three answer

**The idea:** at `comline build` and `comline release`, the consumer's history
numbers each dependency protocol on its connection in the consumer's own
space. It uses the same rules as the consumer's own protocols: the next free
number when the protocol is first added, bound at release, and retired if
removed. The Hello stays one package's, so nothing on the wire changes.

## Shape

```text
test 0.1.0   none::Thing                  #0
test 0.2.0   adds localdeps, reaches Foo  →  localdeps::greeting::Foo  #1 in test's facts
```

- Foo's functions keep the dependency's function numbers. They're unique in
  their protocol already.
- The entry is keyed by **(dependency id, the dependency's wire number)**, not
  by path. A protocol that the dependency renames keeps its number there, so
  it keeps its number here too.
- test's facts copy Foo's shape hash, and record its line as a **test**
  release: the release at which test picked up a breaking change to Foo.

## Where it holds

- **Every peer built from the consumer agrees.** A client and a server both
  generated from `test` read the same facts and get the same numbers. That's
  the common case: an application whose API includes a library's protocol.
- **It's as stable as the consumer's own numbers.** Numbers are assigned,
  bound at release and never reused, by the
  [same rules](../../reference/versioning.md#number). The
  [function-ids decision](../function-ids/annotation.md#as-accepted) rejected a
  hidden ledger of ids because a fresh checkout could assign them differently.
  Wire numbers have lived in history since then, so this adds no new kind of
  risk.
- **No collisions.** Every dependency's protocols share the consumer's one
  space.
- **It isn't unsafe on the wire.** A peer built from the dependency alone
  sends the dependency's package id, and the handshake refuses it
  (`package_mismatch`) before any call. So no frame can reach the wrong
  function. What's lost is reach, not correctness.

## Where it doesn't

1. **Two identities.** Foo is protocol #0 of `localdeps` and #1 of `test`. A peer
   built from `localdeps` alone, such as a generic health checker, can't call
   Foo on test's connection. Two applications that both depend on `localdeps`
   each give Foo their own number. The protocol stops being a contract
   that other packages can reuse: every consumer re-publishes it.
2. **Checked against the wrong version.** The handshake compares test's
   versions, so a change in `localdeps` reaches peers as a change in `test`.
   test must release to move Foo's line. Two test releases built against the
   same `localdeps` release are still judged by test's line for Foo.
3. **Numbers depend on history order.** Two branches that each add a
   dependency both assign their protocols the next number. Reconciling them
   renumbers whatever neither released. That's already true for the
   consumer's own protocols, but adding a dependency now triggers it as well.
4. **Diamonds.** A protocol reached through two paths (`test → a → localdeps`
   and `test → localdeps`) needs one entry. If the paths pin different
   versions of `localdeps`, a rule has to pick whose shape and line the facts
   copy.
5. **Dropping and re-adding a dependency** retires its protocols' numbers, and
   a peer built in between sees `unknown_protocol`. That's consistent with the
   consumer's own protocols, but surprising for a change to `config.idp`.

## Verdict

It works when the consumer means to **re-export** the protocol as part of its
own API, and every peer is built from the consumer. As a default it gives
every dependency protocol a second identity without anyone asking for one, and
it ties the protocol's compatibility to the consumer's releases.

Its one advantage over [A](multi-package-connection.md) is no wire change.
That lasts only until `comline@3` ships. So it isn't recommended as the
mechanism. An explicit "serve this as ours" re-export, one entry at a time,
could be proposed later for packages that want exactly that.
