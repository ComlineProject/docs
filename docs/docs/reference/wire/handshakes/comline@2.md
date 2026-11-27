# `comline@2`

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

## What decides

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
4. A protocol only one end lists is `unknown_protocol`, refused on its own.
   A Hello lists what its end provides and calls, which can be fewer protocols
   than the package has ([below](#what-an-ends-hello-lists)).

## What an end's Hello lists

An end's Hello lists the protocols it provides and every protocol of the other
side that it calls, not necessarily every protocol of the package. The
generated code builds it when a connection opens, from the protocols given to
`Services` or `ClientServices`
([Rust](../../../languages/rust/connections.md#serving-a-subset),
[TypeScript](../../../languages/typescript/connections.md#serving-a-subset)) and
the other side's protocols, which it calls (all of them, so the peer refuses
those it doesn't have). A protocol both ends provide
(`@provider = Multiple`) is listed once, and the entries stay ascending by
number. The rest of the Hello, the package, the version and the encodings, is
the same whichever protocols it lists. A package that provides all of them
sends the Hello the whole connection always did, byte for byte.

A connection carries exactly what its Hello lists:

- **A protocol only one end lists is refused on its own** (`unknown_protocol`),
  and neither end can call it. An end that left a protocol out of its Hello
  doesn't have it on the connection, even if its application could serve it.
  Under `exchange = symmetric` each end's verdict refuses the protocols the
  other lists and it doesn't.
- **An answer or a verdict can't add a protocol.** An answer that names a
  protocol the offer didn't list is `malformed`, and a verdict refusing a
  protocol this end never listed changes nothing about what it agreed.
- **Calls to a protocol outside the result fail locally,** and nothing is sent.
- **Providing one is refused too.** The runtime refuses to register a dispatcher
  for a protocol the handshake didn't accept, not only one the Hello didn't
  list: the peer's refusal is almost certainly a mistake in the application.
  An entry carries no direction, so the runtime can't tell a protocol listed to be
  called from one listed to be provided; the generated code, which knows
  `@provider`, provides only what its side declares. Without a `comline@2`
  Hello (`comline@1`, `none`, a connection opened by hand) there is no result to
  check against.

## Parameters

Written in `@handshake` or `handshake`'s dictionary form
([usage resolution](index.md#usage-resolution)), each value a string or a bare word in `@handshake`,
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

### Hashing and changing them

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

## The exchange

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

## Messages

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

## Reason codes

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
because it lacks the function or because the protocol was refused or isn't in
the result. `Negotiated::accepts` says whether a protocol is in the result and
not refused, and `Negotiated::check_provide` returns the same error for one a
connection mustn't provide. `Hello::build(header, provided, called)` makes a
Hello from the header and the two lists of protocols. In the TypeScript runtime
these are `Negotiated.accepts` and `checkProvide`, `buildHello` and `accepts`.

## Proven by

The `handshake-comline2` vectors in the runtime's corpus
([vectors](https://github.com/ComlineProject/runtime/tree/main/runtime/conformance/spec/vectors)):

- every message type, with byte-exact encodings and malformed variants;
- every step of both exchanges under every parameter value;
- a case for every reason code;
- a Hello listing a subset of the package's protocols (specification 0.12):
  its bytes, offers and answers that name fewer protocols than an end has,
  an answer that goes beyond its offer, and a verdict refusing a protocol
  never listed.

`comline@2`'s profile states `schema_agreement` and `encoding_agreement`,
proven by an accepted peer and by peers refused for a moved line, another
package, other encodings or another exchange.
