# A dependency's protocols on a connection

Status: **decided** (2026-11-14): A and C, with Part 1 · tracked in
[core#277](https://github.com/ComlineProject/core/issues/277), step 0 in
[generation#143](https://github.com/ComlineProject/generation/issues/143) ·
carries out the first decision of
[Connections](../connections.md#several-protocols-on-one-connection), which
`comline@2` was written without

**The question.** A package's dependencies can declare protocols, and the
package can serve or call them. When a dependency's protocol runs on a
connection, **which numbers address it, and which version does the handshake
check it against?**

## Where things stand

- **Wire numbers are per package.** A protocol's
  [number](../../reference/versioning.md#number) is unique in its own package,
  and every package numbers its protocols from 0. So `test::none::Thing` and
  `localdeps::greeting::Foo` can both be protocol 0.
- **A frame names a protocol by that number alone.** A
  [`datagram@3`](../../reference/wire/framings/index.md#datagram3) request carries a
  protocol number and a function number, but no package.
- **A handshake covers one package.** The
  [`comline@2`](../../reference/wire/handshakes/comline@2.md) Hello carries
  one package id and one version, then that package's protocols. Two
  different ids are refused (`package_mismatch`).
- **Profiles don't say any of this.** No fact states how a frame names its
  protocol, what that address is unique in, or how many packages a handshake
  covers. [Part 1](capabilities.md) lists what's missing, and what each gap
  causes today.
- **Connections decided otherwise.** On 2026-10-20 the Connections proposal
  decided that an offer lists protocols by package id plus protocol, and that
  the connection hands out its own numbers, so that "protocols from different
  packages, a dependency's health check say, then share a connection with no
  registry of ids across packages". `comline@2` was written with fixed
  per-package numbers instead, which that page's
  [What's built](../connections.md#whats-built) records as differing from the
  decision.
- **Generation refuses every dependency protocol.** `facts::check` in
  `generation/codegen` addresses every protocol in the request, the
  dependency's included, and looks them up in the package's own facts. A
  dependency that declares a protocol under the default framing and handshake
  then fails `comline generate`, even when the package never uses that
  protocol:

  ```text
  protocol `localdeps/greeting::Foo` uses `datagram@3` with `comline@2`, which
  address it by the wire numbers its package's history assigns, and the
  package's facts have none for it
  ```

  `facts::hello` already skips a dependency's protocols ("not this package's
  to declare"), so the two disagree.

### Step 0, whichever is chosen

A dependency's protocol that the package doesn't reach isn't on its connection.
Generation shouldn't address it, check it, or generate connection code for it.
This fixes the error above for every package that only uses a dependency's
types, and doesn't depend on anything below.

## The pages

| | In one line |
| --- | --- |
| [Part 1 — what framings and handshakes state](capabilities.md) | new profile facts (`protocols`; `packages`, `binds`, `compares`, `refuses`), profile **limits** (how many protocols, functions, errors and pending requests an encoding can address), the capabilities they derive, the rules they make checkable, and what changing an encoding implies |
| [Proposal A](multi-package-connection.md) | several packages on one connection: `comline@3` lists each package with its own id, version and numbers, and binds a connection number per protocol |
| [`datagram@4`](datagram@4.md) | the framing A uses: a protocol by its connection number, a function by its wire number, in a fixed-width header (9-byte request, 5-byte one-way request, 7-byte reply) |
| [Proposal B](consumer-numbers.md) | the consumer's history numbers each dependency protocol it carries in its own space, from when it was added |
| [Proposal C](connection-per-package.md) | each package's protocols run on a connection of their own |

Part 1 stands on its own: its facts are needed whichever proposal is chosen.
The proposals don't all compete. **A** is the general answer, and the
Connections decision already commits to it. **C** is what a protocol gets
when it can't share a connection, and is also a deployment choice. **B** is
the real alternative to A: it avoids changing the wire, at the cost of giving
the protocol a second identity.

## How they compare

| | A: several packages | B: consumer's numbers | C: per package |
| --- | --- | --- | --- |
| Wire change | yes: `comline@3` + `datagram@4` | none | none |
| Identities per protocol | one, its package's | two: the dependency's and the consumer's | one |
| Checked against | the dependency's own version | the consumer's version | the dependency's own version |
| A peer built from the dependency alone can call it | yes | no: different package id | yes |
| State, order and calls both ways shared across packages | yes | yes | no |
| A dependency's handlers see the application's connection state | yes | yes | no |
| A slow dependency handler holds up the application | yes, by default | yes, by default | no |
| Each package keeps its own framing and format | no: one set per connection | no | yes |
| Protocol numbers known before connecting | no | yes | yes |
| Serving part of what the packages declare | per protocol, through the offer | per protocol, as today | per package by connection, then per protocol |
| The dependency's changes move the consumer's version | only for which protocols the connection carries | yes: the consumer re-releases each one | no |
| Peers learn dependency versions | yes, from the Hello | no | yes, per connection |

## Decided

Decided 2026-11-14:

- **Step 0 now.**
- **[Part 1](capabilities.md) is accepted:** its facts, the `one_way` fact,
  and `limits`, for caps the encoding's bytes impose. These are needed
  whichever proposal applies, and close the `datagram@2` protocol-reordering
  gap on their own.
- **[A](multi-package-connection.md) is accepted** for protocols that can
  share a connection, as `comline@3` with [`datagram@4`](datagram@4.md). They
  become the defaults in the next edition, and runtimes may answer a
  `comline@2` initiator during the migration.
- **[C](connection-per-package.md) is accepted** for protocols that can't
  share one, because their framing, handshake or format differs, and for
  deployments that want isolation.
- **[B](consumer-numbers.md) is rejected** as a default. Re-exporting a
  dependency's protocol as the consumer's own could come back as an explicit,
  opt-in act.

The points decided within A are listed on [its page](multi-package-connection.md#as-decided).
