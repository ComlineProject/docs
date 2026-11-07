# Handshakes

What two ends exchange when a connection opens, before the first call:
`comline@2`, the default, which checks compatibility, and `comline@1`, which
checks identity.

`comline@2` is the default where all of a package's protocols are on
`datagram@3`, which is every package that takes the defaults. It runs one
handshake per connection, so a package whose protocols can't share one
(one on `jsonrpc`, `datagram@2` or a lockstep framing, say, or one naming
another handshake) gets `comline@1` for every protocol that names none, as
before. A package's `handshake` in `config.idp` overrides both. See
[Defaults before `comline@2`](#defaults-before-comline2) for what the change
of default means for a released package.

## Official handshakes

| Name | Does | Gives up |
| --- | --- | --- |
| `comline@2` (the default) | exchanges each version's facts, and decides by each protocol's line | nothing, unless `same_version_differs = warn`: then version honesty |
| `comline@1` | exchanges and checks schema, format and framing | nothing |
| `none` | sends and checks nothing | schema agreement and encoding agreement |

`none` is the absence of a handshake, so it is not declared anywhere.

## Usage resolution

A protocol's `@handshake` is picked first, then its package's `handshake` key in `config.idp`, then the official default
(`comline@2`, or `comline@1` in a package whose protocols can't all run `comline@2`):

```ids
@handshake = "com.acme.hello@1"
protocol Gateway { /* ... */ }
```

A handshake that takes [parameters](#parameters) is written as a dictionary
instead, its name under `name`, as `@framing` does. The plain name is shorthand
for a dictionary with only a name:

```ids
@handshake = { name = "comline@2", newer_consumer = refuse }
protocol Gateway { /* ... */ }
```

```title="config.idp"
handshake = { name = "comline@2" scope = "package" }
```

A protocol's own `@handshake` replaces the package's whole: the two aren't
merged.

## `comline@1`

Each end sends one fixed 31-byte frame and refuses unless the peer's
matches:

| Bytes | Field |
| --- | --- |
| 2 | magic, `"CO"` |
| 1 | version, `01` |
| 8 | the schema fingerprint (IR hash), `u64` LE |
| 8 | the format's name hash (FNV-1a 64), `u64` LE |
| 8 | the framing's name hash, `u64` LE |
| 4 | capability bits, `u32` LE (advisory) |

Any edit to the schema changes the fingerprint, so the two ends must have
been built from the same schema.

## `comline@2`

`comline@2` compares what each version's history records
([core#119](https://github.com/ComlineProject/core/issues/119)), not the
whole IR:

- the **package id** (`id` in `config.idp`);
- the **package version**;
- for each protocol: its **wire number**, its **line** (the release at
  which it last broke) and its **wire-shape hash**;
- for each function: its **wire number**;
- for each encoding (format, framing, the handshake itself): its
  **parameter hash**, which covers its name and parameters.

The namespace isn't compared, so renaming one doesn't stop peers from
connecting.

### What decides

1. Different package ids: refused.
2. Different encodings (format, framing or handshake, by parameter hash):
   refused.
3. Per protocol both ends have:
   - **Lines differ:** the protocol broke between the two versions, so it's
     refused. A line moves at a major release from 1.0, and at a minor
     release while the package is 0.x.
   - **Same package version, but the shape hash differs:** one end isn't
     what its version claims. `same_version_differs` decides.
   - **The consumer has functions the provider lacks**, by function number:
     `newer_consumer` decides.
4. A protocol only one end has is `unknown_protocol`, refused on its own.

### Parameters

Written in `@handshake` or `handshake`'s dictionary form
([above](#usage-resolution)), each value a string or a bare word in `@handshake`,
and a string in `config.idp`. Defaults first:

| Parameter | Values | Kind | Meaning |
| --- | --- | --- | --- |
| `scope` | `protocol` \| `package` | policy | A protocol's refusal refuses that protocol alone, or the whole connection. `unknown_protocol` never refuses more than its protocol. |
| `newer_consumer` | `degrade` \| `refuse` | policy | `degrade` connects, and calls to the functions the peer lacks fail locally without reaching the wire. `refuse` refuses the protocol. |
| `same_version_differs` | `refuse` \| `warn` | policy | Refuse the protocol, or connect and report a warning. `warn` gives up version honesty. |
| `exchange` | `offer` \| `symmetric` | wire | Who sends what (below). Both ends must agree: it's part of the handshake's parameter hash and of every hello. |

Each end applies its own policies, and either end's refusal counts. With
`scope = protocol`, a connection whose every protocol is refused is
refused.

An unknown parameter or value is a build error, and so is any parameter on a
handshake that takes none: `comline@1`, `none`, and for now a handshake a
package declares, whose profile can't state parameters.

#### Hashing and changing them

Only `exchange` is in the handshake's parameter hash. The policies aren't, so
two ends with different policies still agree. A parameter written as its default
is the same as one left out, in the hash and in the comparison of two versions:

| Change | Version bump | Line |
| --- | --- | --- |
| `exchange` | major | moves |
| `scope` or `newer_consumer`, either way | patch | stays |
| `same_version_differs`, `warn` to `refuse` | patch | stays |
| `same_version_differs`, `refuse` to `warn` | major | stays |
| writing a default out, or dropping it | none | stays |

`same_version_differs = warn` gives up **version honesty**: two peers of the same
version may turn out to have different shapes. As with
[any guarantee given up](../../../guides/idl/protocol.md#giving-up-a-guarantee), it
needs `@unverified` on the protocol to build, and each consumer accepts it. The
major bump tells consumers so, but nothing on the wire changed, so the line stays
and peers on it keep connecting.

### The exchange

=== "offer"

    ```mermaid
    sequenceDiagram
        participant C as Initiator (consumer)
        participant S as Responder (provider)
        C->>S: Hello: package, encodings, protocols
        S->>C: Answer: per protocol, accepted (+ missing functions) or refused
        C->>S: Verdict: accept (+ protocols it refuses) or refuse
    ```

=== "symmetric"

    ```mermaid
    sequenceDiagram
        participant C as Initiator
        participant S as Responder
        C->>S: Hello
        S->>C: Hello
        C->>S: Verdict
        S->>C: Verdict
    ```

There is one handshake per connection. A refusal ends it: the refusing end
sends its refusal and stops.

### Messages

Every message starts with `"CO"`, the version byte `02` and a type byte.
Numbers and counts are shortest-form varints, a hash is 16 bytes (the
first 128 bits of core's blake3 hash), and a release is three varints:
major, minor, patch. Bytes after a message's last field make it malformed.

**Hello** (type `01`):

| Field | Bytes |
| --- | --- |
| `exchange` | 1: `00` offer, `01` symmetric |
| package id | 16 |
| package version | a release, then the pre-release (`dev.2`): length varint + UTF-8, `00` for none |
| encodings | count, then each: kind (1: `00` format, `01` framing, `02` handshake) + parameter hash (16), ascending |
| protocols | count, then each: number, line (a release), shape hash (16), function numbers (count + numbers, ascending), ascending by number |

**Answer** (type `02`, from the responder under `offer`):

- `00` accept: the responder's package version, then a count and, for every
  offered protocol in the offer's order, its number and a status:
  - `00` accepted, or `01` accepted with the shape hash differing, each
    followed by the offered functions the responder lacks (count +
    numbers);
  - `02` refused, followed by the reason code.
- `01` refuse, followed by a refusal.

**Verdict** (type `03`):

- `00` accept, followed by the protocols this end refuses: count, then each
  number + reason code, ascending;
- `01` refuse, followed by a refusal.

**Refusal:** the reason code (1 byte), the refusing side (1 byte: `00`
initiator, `01` responder), then the protocol number when the reason is
about one protocol.

For example, an initiator refusing the connection over protocol 1's line:

```text
434f 02 03 01  06 00 01
"CO" v2 verdict refuse  line_mismatch initiator protocol 1
```

### Reason codes

Stable: a code is never renumbered or reused.

| Code | Reason | About | When |
| --- | --- | --- | --- |
| 1 | `malformed` | connection | The peer's message didn't parse. |
| 2 | `handshake_version` | connection | The peer speaks another handshake version, such as a `comline@1` frame. |
| 3 | `exchange_mismatch` | connection | The two ends declare different `exchange` values. |
| 4 | `package_mismatch` | connection | The package ids differ. |
| 5 | `encoding_mismatch` | connection | The encodings' parameter hashes differ. |
| 6 | `line_mismatch` | a protocol | The protocol's lines differ. |
| 7 | `same_version_differs` | a protocol | The versions are equal but the shape hash differs, under `same_version_differs = refuse`. |
| 8 | `newer_consumer` | a protocol | The consumer has functions the provider lacks, under `newer_consumer = refuse`. |
| 9 | `unknown_protocol` | a protocol | Only one end has the protocol. |

In the Rust runtime, a refusal is `RuntimeError::Refused { reason, side }`
on both ends. After a successful handshake, `Negotiated::check_call`
returns `RuntimeError::Unavailable` for a call the peer can't take, either
because it lacks the function or because the protocol was refused.

### Proven by

The `handshake-comline2` vectors in the runtime's corpus
([vectors](https://github.com/ComlineProject/runtime/tree/main/runtime/conformance/vectors)):

- every message type, with byte-exact encodings and malformed variants;
- every step of both exchanges under every parameter value;
- a case for every reason code.

`comline@2`'s profile states `schema_agreement` and `encoding_agreement`,
proven by an accepted peer and by peers refused for a moved line, another
package, other encodings or another exchange.

## Defaults before `comline@2`

Until `comline@2` became the default, a protocol that named no handshake ran
`comline@1`, on `datagram@2`. A version built then is read as it was built:
its facts record the encodings it used, and one built before they were
recorded reads as `datagram@2` and `comline@1`, never as today's defaults.

So a package that takes the defaults shows a wire change on its first build
after the change: each protocol's framing and handshake change, its line
moves, and the next release takes a breaking bump (a minor one in 0.x). A
peer built from an older release refuses it, as it would any wire change.

To keep the old wire instead, state it in `config.idp`:

```idp
wire = { framing = "datagram@2" }
handshake = "comline@1"
```

A package that states them sees no change: not in its IR, its facts or its
version. Either can also be stated on its own, per protocol, with
`@framing` and `@handshake`.

