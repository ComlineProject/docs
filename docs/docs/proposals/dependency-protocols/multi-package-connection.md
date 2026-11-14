# Proposal A — several packages on one connection

Status: **accepted** (2026-11-14), as [decided below](#as-decided) · builds on
[Part 1](capabilities.md) · See the [section overview](index.md) for the
question all three answer

**The idea:** a connection carries protocols from several packages. The
handshake, `comline@3`, lists each package with its own id, version and
protocols, and binds each protocol a connection number. The framing,
[`datagram@4`](datagram@4.md), addresses a protocol by that number. Each
package's wire numbers, lines and versions stay its own, so a dependency's
protocol keeps its one identity wherever it's served. This is the first
decision of [Connections](../connections.md#several-protocols-on-one-connection),
written for `comline@2`'s successor.

## Shape

`test` serves its own `Thing` and its dependency's `Foo` on one connection:

```text
packages on the connection     wire numbers            connection numbers
localdeps  (id 0730…, 0.2.0)   greeting::Foo   #0  →   0
test       (id a5d4…, 0.4.0)   none::Thing     #0  →   1
```

Both protocols are #0 in their own packages, and the connection tells them
apart. Function numbers stay their package's own: they're unique in their
protocol, so they never collide.

In Part 1's terms, the pairing states `protocols = by_binding`,
`packages = several` and `binds = protocols`, which is what
[several packages on one connection](capabilities.md#capabilities-what-a-pairing-can-do)
requires.

## Why a new framing

`datagram@3`'s protocol field is a package wire number (`protocols = by_id`).
A field that's sometimes a wire number and sometimes a connection number
would be one profile stating two facts. A profile is fixed for its version,
so a different fact means a new version: `datagram@4` (`protocols =
by_binding`). It's specified in full on [its own page](datagram@4.md).

## The handshake: `comline@3`

`comline@3` checks compatibility from each version's facts, for every package
on the connection.

### Messages

Every message starts with `"CO"`, the version byte `03`, and a type byte.
Numbers and counts are shortest-form varints, and a hash is 16 bytes (the
first 128 bits of core's blake3 hash). A release is three varints (major,
minor, patch), and a package version is a release followed by its pre-release
(length varint and UTF-8, or `00` for none). Bytes after a message's last
field make it malformed.

**Hello** (type `01`):

| Field | Bytes |
| --- | --- |
| `exchange` | 1: `00` offer, `01` symmetric |
| encodings | the connection's format, framing and handshake: count, then each kind (1: `00` format, `01` framing, `02` handshake) and parameter hash (16), ascending |
| packages | count, then each: package id (16), package version, protocols; ascending by package id |
| protocols, per package | count, then each: wire number, line (a release), shape hash (16), function numbers (count, then numbers, ascending); ascending by wire number |

**Answer** (type `02`, from the responder under `offer`):

- `00` accept: then, for every package in the offer's order, the responder's
  version of it (or `00` and no version when it doesn't have that package).
  Then, for every offered protocol in connection-number order, a status:
  - `00` accepted, or `01` accepted with the shape hash differing, each
    followed by the offered functions the responder lacks (count + numbers);
  - `02` refused, followed by the reason code.
- `01` refuse, followed by a refusal.

**Verdict** (type `03`):

- `00` accept, followed by the protocols this end refuses: count, then each
  connection number + reason code, ascending;
- `01` refuse, followed by a refusal.

**Refusal:** the reason code (1 byte), the refusing side (1 byte: `00`
initiator, `01` responder), then the connection number when the reason is
about one protocol.

The exchanges are `comline@2`'s: under `offer`, the initiator sends Hello,
the responder sends Answer, and the initiator sends Verdict. Under
`symmetric`, both send Hello, then both send Verdict.

### Connection numbers

A protocol's **connection number** is its position in the initiator's Hello,
counting across packages in order.

- Both ends know the numbers once the initiator's Hello has arrived, under
  `offer` and `symmetric` alike, so no message has to carry them. Connections
  had the server's answer hand them out. The answer lists protocols in the
  offer's order, so the position *is* the number.
- A protocol only the responder has is `unknown_protocol`, and never needs
  a number.

### What decides

1. Another handshake version (`"CO"` with a version byte other than `03`):
   refused, `handshake_version`.
2. Different encodings, by parameter hash: refused, `encoding_mismatch`.
3. Per package both ends list, and per protocol of it both have, comparing
   **that package's** versions:
   - the lines differ: the protocol is refused, `line_mismatch`;
   - same package version but a different shape hash: `same_version_differs`
     decides;
   - the consumer has functions the provider lacks: `newer_consumer` decides.
4. A protocol only one end has, including every protocol of a package only one
   end lists: `unknown_protocol`, refused on its own.

The reason codes are `comline@2`'s. `package_mismatch` (4) no longer arises,
and stays reserved because codes are never reused.

### Parameters

`comline@2`'s four, with one value added to `scope`:

| Parameter | Values | Meaning |
| --- | --- | --- |
| `scope` | `protocol` \| `each_package` \| `package` | A refusal takes down the protocol alone, every protocol of its package, or the whole connection. `package` keeps `comline@2`'s meaning, the whole connection, so switching a config from `comline@2` to `comline@3` never silently narrows a refusal. `unknown_protocol` never takes down more than its protocol. |
| `newer_consumer` | `degrade` \| `refuse` | as `comline@2` |
| `same_version_differs` | `refuse` \| `warn` | as `comline@2`, per package |
| `exchange` | `offer` \| `symmetric` | as `comline@2`; in the parameter hash |
| `accept_previous` | `false` \| `true` | a policy: also answer a `comline@2` initiator ([migration](#for-the-wire-and-peers)). Not in the parameter hash: it changes no byte for `comline@3` peers. Valid only when the package has a release built on the old wire |

## Which dependency protocols join

- **Reached by `use`.** A dependency's protocol is on the package's
  connection when a schema of the package `use`s it:

  ```ids
  use localdeps::greeting::Foo
  ```

  That's the same rule [Dependencies](../schema-compatibility.md#dependencies)
  uses for versions. Declaring a dependency puts nothing on the wire, and
  `use` of a protocol is new: today `use` names types and other declarations.
- **All three encodings must match.** A dependency's protocol joins only when
  its own resolved framing, handshake and format are the connection's, by
  parameter hash in the dependency's facts. They're part of the dependency's
  contract (changing them is major there), and its shape hash covers what it
  puts on the wire in its own format, so the consumer can't re-host it on
  others. Otherwise it gets a [connection of its own](connection-per-package.md),
  and the build says which encoding differs.
- **One version per package per end.** An end lists each package once. If
  the package reaches one dependency through two paths that pin different
  versions, the build refuses it, naming both paths.
- **Every package needs an `id`.** `comline@3` identifies each package by its
  id, and a dependency built without one can't join.
- **Releases only, for releases.** Numbers are
  [bound at release](../../reference/versioning.md#number). `comline generate`
  takes a dependency's numbers from its pinned version, and warns when that
  version is a pre-release. `comline release` refuses a dependency at a
  pre-release version whose protocols are on its connection, because
  [consumers only see releases](../schema-compatibility.md#builds-and-releases).

## Implications

### For the wire and peers

- **A wire change for every package that takes the defaults.** Switching the
  defaults from `datagram@3` + `comline@2` to `datagram@4` + `comline@3`
  moves every protocol's line, so the next release is a breaking one (minor
  in 0.x). As with the last change of defaults, it should come with a new
  edition. A version built before it reads as built, and stating `wire =
  { framing = "datagram@3" }` and `handshake = "comline@2"` keeps the old
  wire.
- **`comline@2` peers during the migration (dual-accept).** A package that
  sets `accept_previous = true` also answers a `comline@2` initiator. An
  initiator always speaks its own version, so only responders do this.
  - **It switches the whole wire, not only the handshake.** The responder
    reads the version byte (`02` or `03`) and runs that exchange. A `comline@2`
    connection then runs as `comline@2` would: one package, `datagram@3`,
    protocols by package wire number, and no dependency protocols.
  - **It serves the old contract.** Switching the defaults moved every line,
    so answering an old peer with the new release's facts would refuse every
    protocol (`line_mismatch`). The old-wire path presents the **last release
    built on the old wire**: its version, lines and Hello. Generated code
    embeds those facts beside the new ones, read from history by the CLI.
  - **It lives in the shared runtime core,** written once for every
    language that binds it, beside the `comline@2` exchange the C ABI already
    runs. A connection's framing is decided at connect time, as an enum of the
    two connection types, so nothing branches per call afterwards. The ABI
    gains a mode where the handshake chooses the framing (additive, at 0.x).
    A host running without the core, such as TypeScript's fallback, refuses
    old peers (`handshake_version`), and its support claim says so.
  - **It's temporary.** `accept_previous` is dropped in a later edition.
  - A package that doesn't set it refuses old peers (`handshake_version`).
    A gateway translating `comline@2` to `comline@3` is possible for
    operators, but it breaks end-to-end agreement, so it isn't the mechanism.
- **The Hello grows** by 16 bytes for each extra package id, plus a version
  for each. It's sent once per connection.
- **Dependency versions become visible to peers.** The Hello carries the
  version of every package on the connection, so a peer learns which version
  of each dependency the other end runs. `comline@2` already reveals the
  package's own version. Where that matters, the package keeps the
  dependency off the connection ([C](connection-per-package.md)).
- **Partial connections become routine.** A peer built against an older
  `localdeps` sees `Foo` refused (`line_mismatch`) while `Thing` works.
  Generated code already returns `Unavailable` for a refused protocol, so a
  caller must expect it for any dependency protocol.

### For versions

- **The consumer's version covers which protocols its connection carries.**
  Adding a dependency's protocol is minor, and removing one is major, just like
  adding or removing a function. Moving a dependency's protocol between this
  connection and a [connection of its own](connection-per-package.md) is
  major.
- **The protocol's own changes are the dependency's.** They move its line in
  the dependency's history, and the handshake compares the dependency's
  versions, so the consumer doesn't re-release them. Its reach into the
  dependency's types counts as it does today.
- **Upgrading a dependency is a consumer change** only as far as it reaches:
  a dependency release that moves `Foo`'s line makes `Foo` unavailable to
  peers on the old line, without touching `Thing`.

### For generated code and runtimes

- **Protocol numbers aren't constants any more.** Generated code names a
  protocol by (package id, wire number). The runtime maps that to a connection
  number after the handshake, and each call pays one table lookup. Under
  `datagram@3`, the number is a constant in the code.
- **A connection's providers and senders span packages.** `Services`, `serve`
  and `connect` take the dependency's providers too. The dependency's
  generated module exposes its providers and senders, and the consumer's
  connection carries them.
- **Shared connection state.** A dependency's handlers see the connection's
  extensions: authentication, session, whatever interceptors put there. That
  includes the application's state. A dependency that shouldn't see it
  belongs on its own connection.
- **Shared order.** A connection runs one call at a time by default, so a
  slow dependency handler holds up the application's calls (head-of-line
  blocking). The async driver's concurrency applies across packages.
- **Errors stay per schema.** A reply names its protocol, so an error ordinal
  is read in the error space of the schema that declares that protocol, in
  whichever package.
- **`comline@3` runs in every runtime.** That means the Rust and TypeScript
  runtimes, and the shared core with its C ABI and WASM build
  ([Shared runtime core](../shared-runtime-core/index.md)), still at 0.x,
  where a new handshake is additive.

### For the toolchain

- **`comline generation` reads dependency history.** For each dependency
  whose protocols are on the connection, it reads that dependency's facts
  from its history at the pinned version. A dependency fetched without its
  `.comline` history can't provide them, so publishing has to include the
  facts.
- **`comline inspect`** shows the connection's packages, each protocol's
  connection position, and the [capabilities](capabilities.md#capabilities-what-a-pairing-can-do).
- **Conformance** gains `handshake-comline3` and `framing-datagram4` vectors
  and features, and each generator claims them.
- **JSON-RPC can't follow yet.** A qualified method name is
  `namespace.Protocol/function`, unique in a package but not across packages,
  so two packages' protocols can collide. Carrying several packages on
  JSON-RPC would need a `method_names` value that names the package too: a
  parameter that sets `protocols`, not a new version.

## What it touches

- **runtime:** `comline@3`'s messages, decisions and vectors; `datagram@4`
  and its vectors; dual-accept in the shared core, with a connection decided
  at connect time and an ABI mode where the handshake picks the framing, and
  vectors for a `comline@3` responder answering a `comline@2` initiator; the table from (package id, wire number) to connection
  number; `Negotiated::check_call` and the dispatch table keyed by connection
  number; profiles with the [new facts](capabilities.md#proposed-facts).
- **generation:** `GenerateRequest` carries facts per package: the package's
  own, plus one set per dependency reached. `check`, `addressing` and `hello`
  look each protocol up in its own package's facts. Generated code names a
  protocol by (package id, wire number) and resolves it after the handshake.
  Under `accept_previous`, it also embeds the last old-wire release's facts.
- **cli:** `comline generation` reads and passes each reached dependency's
  facts, and under `accept_previous` the last old-wire release's, and enforces
  the release rule above. Publishing includes facts.
- **core:** `use` of a protocol, reaching a dependency's protocol through it,
  the consumer's version rules
  above, the build errors of [Part 1](capabilities.md#rules-the-facts-make-checkable),
  and `comline@3` and `datagram@4` as official encodings.

## As decided

Decided 2026-11-14, with the [section](index.md#decided):

- **Reach is by `use`** of the protocol ([above](#which-dependency-protocols-join)).
- **Framing, handshake and format must all match** for a dependency's
  protocol to join. Otherwise it takes a connection of its own.
- **`scope` is `protocol` | `each_package` | `package`**, where `package`
  keeps meaning the whole connection ([Parameters](#parameters)).
- **The default in the next edition** is `comline@3` with `datagram@4`.
- **Dual-accept** is opt-in per package (`accept_previous`, outside the
  parameter hash), lives in the shared runtime core, and serves the last
  old-wire release's facts, which generation embeds
  ([above](#for-the-wire-and-peers)).
- **`use` of a protocol is a reach only,** for now: it puts the protocol on the
  connection, and doesn't alias or re-export it.
- **`datagram@4`'s layout** is fixed widths, a `u32` request id, a one-way
  kind, and the protocol kept in replies
  ([why](datagram@4.md#why-fixed-widths)). The runtime's benchmark gates
  should confirm it against `datagram@3`.

## Open questions

- **How `comline inspect` shows** which protocols a connection carries,
  its own and its dependencies'.
