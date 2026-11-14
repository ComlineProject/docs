# Part 1 — what framings and handshakes state

Status: **accepted** (2026-11-14), with the `one_way` fact and `limits` · tracked in
[core#276](https://github.com/ComlineProject/core/issues/276) · a
prerequisite of the [proposals](index.md) in this section · extends the [encoding profiles](../schema-compatibility.md#encoding-profiles)
of Schema compatibility

**The question.** A profile states facts about its encoding, and the toolchain
turns those facts into decisions: which bump a change takes, what a build
refuses, and which guarantees a protocol keeps. **Do today's facts say
everything a framing and a handshake can and can't do?** They don't, and
carrying a dependency's protocols on a connection depends on the parts they
leave out.

## What profiles state today

| Fact | Applies to | Values | What reads it |
| --- | --- | --- | --- |
| `calls` | framing | `by_index`, `by_name`, `by_id` | the comparison: inserting or reordering functions |
| `directions` | framing | `both`, `one` | the build: `@provider = Client` / `Multiple` needs `both` |
| `errors` | framing | `by_ordinal`, `by_name` | the comparison: inserting or reordering errors |
| `payload` | framing | `opaque`, `json` | the build: the format's `output` must fit it |
| `schema_agreement` | handshake | `true`, `false` | guarantees: schema agreement |
| `encoding_agreement` | handshake | `true`, `false` | guarantees: encoding agreement |

## What they leave unsaid

Each gap below has a concrete consequence today.

1. **How a frame names its protocol.** `calls` says how a request names its
   *function*. Its `by_id` value is described as "by the protocol's and
   function's wire numbers", so one fact answers two questions, and only for
   one framing. Nothing states that `datagram@2` names a protocol by its
   *position in the package*. As a result, the comparison has no rule for
   inserting or reordering protocols. Under `datagram@2`, adding a protocol
   to an earlier schema silently re-addresses every protocol after it, and
   the version doesn't say so.
2. **What a protocol's address is unique in.** A number unique in one
   package, one unique in a connection, and a name unique in a package can't
   be told apart. This is the question this section exists for: whether two
   packages' protocols can share a connection.
3. **How many packages a handshake covers.** `comline@1` hashes one
   package's IR, and `comline@2` sends one package id. No fact says so. The
   rule only shows up as a refusal (`package_mismatch`) at run time.
4. **Whether a handshake binds anything.** A framing whose numbers come from
   the handshake can only run under a handshake that hands them out. No fact
   lets the build check that pairing.
5. **What a handshake compares.** `comline@1` compares identity (one IR
   hash), and `comline@2` compares compatibility (lines, shapes, numbers).
   Both state `schema_agreement = true`. What that means for upgrades isn't
   stated: under identity, every peer must be rebuilt from the same schemas,
   while under compatibility a compatible older peer still connects.
6. **What a refusal takes down.** `comline@1` refuses the connection.
   `comline@2` refuses one protocol or the connection, depending on its `scope`
   parameter. Generated code has to handle a protocol being `Unavailable` only
   in the second case, and nothing states it.
7. **What a change of encoding implies.** Changing a framing or handshake is
   major, and moves every line on it. Nothing says what the package gains or
   loses by the change, or what it newly requires, such as build history or
   a package `id`.

## Proposed facts

Same rules as the existing ones: a small, fixed set, each value proven by
conformance vectors, fixed for a version, and settable by a parameter where the
encoding has one.

### Framing

| Fact | Description | Values |
| --- | --- | --- |
| `calls` (narrowed) | How a request names the **function** it calls, within its protocol. | `by_index`: its position · `by_name`: its name · `by_id`: its wire number |
| `protocols` (new) | How a request names the **protocol** it calls into. | `unnamed`: it doesn't, so the connection carries one protocol · `by_index`: its position among its package's protocols · `by_name`: its qualified name, `namespace.Protocol` · `by_id`: its wire number in its package · `by_binding`: a number the handshake binds for the connection · `in_call`: it doesn't, but the function's id is unique across every protocol on the connection, so it picks out the protocol too (a flat opcode table) |
| `correlation` (from [Packet dispatch](../packet-dispatch/index.md#comlines-own-packet-framing)) | How a reply is matched to its request. | `none`: there are no replies · `header_id`: by an id in the header |
| `one_way` (new) | How a frame tells apart a call that gets no reply. | `by_schema`: it doesn't; both ends know from the function's declaration · `in_frame`: the frame says so (a request kind, a notification) |
| `handles` (new, from [IPC](../ipc.md#who-ties-handles-to-a-frame)) | How a frame's OS handles are tied to it. | `none`: the framing can't carry any · `by_transport`: the transport delivers them with the frame · `counted`: the header counts them · `indexed`: the frame lists where each one is |

`handles` is `by_transport` for `datagram@1` to `@4` and `jsonrpc@1`, and
`none` for `comline.packet@1`. `counted` and `indexed` are for platform
framings such as D-Bus and Binder.

Narrowing `calls` changes only its description. No value and no profile
changes.

**What a protocol's address is unique in** follows from `protocols`, so it
isn't a fact of its own:

| `protocols` | The address is unique in | So a connection can carry |
| --- | --- | --- |
| `unnamed` | nothing: there's one protocol | one protocol |
| `in_call` | its function ids, per phase and direction, across the connection | one package's protocols, with ids unique across all of them |
| `by_index`, `by_id` | its package | one package's protocols |
| `by_name` | its package (namespaces are unique in a package, not across packages) | one package's protocols |
| `by_binding` | the connection | protocols from several packages, if the handshake lists them |

Caps on how much a framing can address are numbers, not facts: see
[Limits](#limits).

### Handshake

| Fact | Description | Values |
| --- | --- | --- |
| `packages` | How many packages one connection's handshake covers. | `one` · `several` |
| `binds` | What the handshake assigns for the connection's frames to use. | `nothing` · `protocols`: a connection number per protocol |
| `compares` | What decides whether two ends may talk. | `identity`: both built from the same schemas · `facts`: each version's lines, shapes and numbers, so compatible versions connect |
| `refuses` | The least a refusal takes down. Set by a `scope` parameter where the handshake has one. | `connection` · `package` · `protocol` |

## The official encodings, stated in full

### Framings

| framing | `calls` | `protocols` | `directions` | `errors` | `payload` |
| --- | --- | --- | --- | --- | --- |
| `datagram@1` | `by_index` | `unnamed` | `one` | `by_ordinal` | `opaque` |
| `datagram@2` | `by_index` | `by_index` | `both` | `by_ordinal` | `opaque` |
| `datagram@3` | `by_id` | `by_id` | `both` | `by_ordinal` | `opaque` |
| [`datagram@4`](datagram@4.md) | `by_id` | `by_binding` | `both` | `by_ordinal` | `opaque` |
| `jsonrpc@1`, `method_names = bare` | `by_name` | `unnamed` | `both` | `by_ordinal` | `json` |
| `jsonrpc@1`, `method_names = qualified` | `by_name` | `by_name` | `both` | `by_ordinal` | `json` |
| `comline.packet@1` | `by_id` | `by_id`, or `in_call` with `family = "none"` | `both` | `by_ordinal` | `opaque` |

`comline.packet@1`'s parameters set its facts and limits: see
[What each parameter sets](../packet-dispatch/index.md#what-each-parameter-sets).
Under `correlation = none` every frame is a request, so `directions` is
`both` with no kind marker.

`jsonrpc@1`'s `method_names` parameter is the first framing parameter that
sets a fact. Profiles already allow that.

`one_way` is `by_schema` for `datagram@1` to `@3`, and `in_frame` for
`datagram@4` (a request kind of its own), `jsonrpc@1` (a notification) and
`comline.packet@1` with correlation (kind `02`). Without correlation, every
`comline.packet@1` packet is one-way. Only under `in_frame` can a receiver stay silent for a one-way
call it can't take, since under `by_schema` it can't tell the call was
one-way. [Return forms](../return-forms.md) builds its quiet and acknowledged
forms on this fact.

### Handshakes

| handshake | `packages` | `binds` | `compares` | `refuses` | agreements |
| --- | --- | --- | --- | --- | --- |
| none | (none checked) | `nothing` | (nothing) | (never) | neither |
| `comline@1` | `one` | `nothing` | `identity` | `connection` | schema, encoding |
| `comline@2` | `one` | `nothing` | `facts` | `protocol` or `connection` (`scope`) | schema, encoding |
| [`comline@3`](multi-package-connection.md#the-handshake-comline3) | `several` | `protocols` | `facts` | `protocol`, `package` or `connection` (`scope`) | schema, encoding |

## Capabilities: what a pairing can do

A **capability** is derived from a framing's and a handshake's facts. It's
never stated on its own, so it can't disagree with them. `comline inspect`
would show the capabilities per protocol, beside the guarantees it shows today.

| Capability | Holds when |
| --- | --- |
| several protocols on one connection | `protocols` isn't `unnamed` |
| several packages on one connection | `protocols = by_binding`, and the handshake has `packages = several` and `binds = protocols`; or every id is fixed in the schema (`comline.packet@1`) and the build proves them disjoint across the packages |
| calls in both directions | `directions = both` |
| inserting or reordering functions keeps their address | `calls` is `by_name` or `by_id` |
| inserting or reordering protocols keeps their address | `protocols` is `by_name`, `by_id`, `by_binding` or `in_call` |
| a compatible older or newer peer connects | `compares = facts` |
| a refused protocol leaves the rest working | `refuses` is `protocol` or `package` |
| needs the package's build history to generate | `calls = by_id`, `protocols` is `by_id` or `by_binding`, or `compares = facts` |
| needs a package `id` | `compares = facts` |
| numbers are known before connecting | `protocols` isn't `by_binding` |

For the official pairings:

| | several protocols | several packages | both directions | reorder functions | reorder protocols | compatible peers | partial refusal |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `datagram@1` + `comline@1` | no | no | no | no | (one) | no | no |
| `datagram@2` + `comline@1` | yes | no | yes | no | **no** | no | no |
| `datagram@3` + `comline@2` | yes | no | yes | yes | yes | yes | yes |
| `datagram@4` + `comline@3` | yes | **yes** | yes | yes | yes | yes | yes |
| `jsonrpc@1` qualified + `comline@1` | yes | no | yes | yes | yes | no | no |

## Rules the facts make checkable

**Build errors**, each naming the facts that decide it:

- `protocols = by_binding` without a handshake that has `binds = protocols`:
  nothing would hand out the numbers.
- Protocols of several packages on one connection, unless `protocols = by_binding`,
  `packages = several` and `binds = protocols` all hold, or every id is fixed
  in the schema and proven disjoint across the packages, per phase and
  direction ([packet dispatch](../packet-dispatch/index.md#packages-on-a-packet-connection)).
- Two protocols on a connection whose framing has `protocols = unnamed`
  (`jsonrpc@1`'s ambiguous bare names already fail this way).
- `compares = facts` in a package without an `id`. It fails at generation
  today, and would fail at build instead.
- The existing rules, restated against facts: a format's `output` must fit the
  framing's `payload`, and `directions = one` allows no calls from the
  provider where calls have replies. Under `correlation = none` there are
  none, so packets travel both ways without a kind marker.

**Version comparison**, with the new rows it gains:

| Change | Bump |
| --- | --- |
| insert, remove or reorder protocols, so that one's position in the package moves | major where `protocols = by_index` (`datagram@2`); none elsewhere |
| a protocol's qualified name changes (namespace or protocol renamed) | major where `protocols = by_name`; none where it's `by_id` or `by_binding` |
| the set of a dependency's protocols on the package's connection | minor to add one, major to remove one, where `packages = several` |

## What changing an encoding implies

Changing a protocol's framing or handshake is already major, and moves its
line. With the facts above, the comparison and `comline inspect` can say
what the change does, beyond "the bytes differ":

| Change | Gains | Loses | Newly needs |
| --- | --- | --- | --- |
| `datagram@2` → `datagram@3` | inserting or reordering functions and protocols keeps addresses | numbers readable from the schema alone | build history (wire numbers) |
| `datagram@3` → `datagram@4` | several packages on a connection | protocol numbers known before the handshake | a handshake with `binds = protocols` (`comline@3`) |
| `datagram@*` → `jsonrpc@1` | readable frames, and addresses that survive reordering | binary formats (`payload = json`), and several protocols unless `qualified` | a format whose `output` is `json` |
| `comline@1` → `comline@2` | compatible peers connect, and per-protocol refusal | nothing | a package `id`, build history, releases |
| `comline@2` → `comline@3` | several packages on a connection | nothing | a framing with `protocols = by_binding` for several packages |
| any → none | no handshake round trip | schema and encoding agreement (needs `@unverified`), several packages, any `by_binding` framing | nothing |

The reported reason names what's lost, such as "major: `datagram@4` numbers
protocols per connection; peers on `datagram@3` are refused". It also names
what the package must now have, such as "needs `comline@3`".

## Limits

**The question.** A framing's fields have widths, and widths cap how much the
framing can address. **Should a profile state those caps?** Today none does:
no profile says "this framing addresses at most N functions".

### Why it hasn't mattered, and why it will

So far, every official framing's caps happen to equal core's: wire numbers are
`u16`, and so are the datagram framings' protocol and function fields. The
coincidence hides the gap.

[Packet dispatch](../packet-dispatch/index.md) breaks it. `comline.packet@1` takes
an `id` width parameter, `id = "u8"` among them. Under it, a protocol's
257th function, or an `@id = 300`, has a number the frame can't hold. Nothing
in the build knows the framing's width, so nothing refuses it. A third-party
framing with narrow fields has the same problem.

### Proposed: `limits` beside `facts`

A profile gains a `limits` map. Each limit is a number, with `value` and
`proven_by` like a fact, proven by vectors at the limit. Like facts, a limit
is fixed for the encoding's version, and **a parameter can set it**
(`comline.packet@1`'s `id = "u8"` sets `functions_per_protocol` to 256).

Limits aren't facts, because they're used differently. A fact is one of a
few values that rules compare between two versions. A limit is a number that
the build checks the package's counts against.

| Limit | Applies to | What it caps |
| --- | --- | --- |
| `protocols` | framing | protocols one address space holds. The space is the one the `protocols` fact names: a package, or a connection under `by_binding` |
| `functions_per_protocol` | framing | the largest function number, plus one |
| `errors_per_schema` | framing | the largest error ordinal, plus one |
| `pending_requests` | framing | requests awaiting a reply at once, per direction |
| `frame_bytes` | framing | the largest frame, when the framing writes the frame's length itself (`comline.packet@1`'s `length`). Otherwise the transport delimits frames, and the cap is the transport's |
| `handles_per_frame` | framing | the most handles one frame carries, for a framing that counts or lists them (`handles = counted` or `indexed`). Under `by_transport` the cap is the transport's per message |
| `packages_per_connection` | handshake | packages one handshake lists |
| `protocols_per_connection` | handshake | protocols one handshake lists |

Format limits (items in a collection, bytes in a string, enum variants, union
members) would take the same shape, as a follow-up.

### The official framings' limits

| framing | `protocols` | `functions_per_protocol` | `errors_per_schema` | `pending_requests` |
| --- | --- | --- | --- | --- |
| `datagram@1` | 1 | 65536 | 65536 | 2⁶⁴ |
| `datagram@2` | 65536, per package | 65536 | 65536 | 2⁶⁴ |
| `datagram@3` | 65536, per package | 65536 | 65536 | 2⁶⁴ |
| [`datagram@4`](datagram@4.md#limits) | 65536, per connection | 65536 | 65536 | 2³² |
| `jsonrpc@1` | (none) | (none: by name) | (none) | (none) |
| `comline.packet@1`, `id = "u8"`, `family = "u8"`, `correlation = { header_id = "u16" }` | 256, per package | 256 | per its error status (undecided) | 2¹⁶ |

"(none)" means the encoding's bytes impose no cap. Core's own still applies:
wire numbers are `u16`, so a package has at most 65536 protocols, and a
protocol at most 65536 functions.

### What reads them

- **The build.** It checks every count against the smallest cap in play:
  core's, the framing's and the handshake's. The error names the limit, the
  encoding, and the parameter that set it: ``protocol `game::Login` has 300
  functions, and `comline.packet@1` with `id = "u8"` addresses at most 256``.
  The same check applies to an `@id` above the cap.
- **The comparison.** A limit doesn't change bytes, so it takes no bump of
  its own. Changing to an encoding or parameter with a lower cap is already
  major. A change that would exceed a cap is a build error, never a bump.
- **`comline inspect`.** It shows headroom: "12 of 256 functions".
- **Runtimes.** `pending_requests` bounds a caller's table of requests in
  flight. A caller at the cap waits, or refuses the call, instead of reusing
  an id that's still pending.
- **Generators.** They can size what they emit, such as a `u8` dispatch index
  under a `u8` framing.

### What stays out

A profile states only the caps its **encoding's bytes** impose. Others belong
elsewhere:

| Limit | Where it belongs |
| --- | --- |
| a runtime's language, such as JSON numbers above 2⁵³ in TypeScript | the language's support tables, and the generator's feature claims |
| the largest frame, where the transport delimits frames | the transport's profile ([Transports](../transports.md)). A framing that writes the length itself states `frame_bytes` |
| core's `u16` wire numbers | core: [Number](../../reference/versioning.md#number) |
| a type's bound, such as `char[max 64]` | the schema |

### Is it worth it?

- **For:**
  - It's the only thing that catches a narrow encoding's overflow at build
    time, rather than as truncation or a refusal at run time.
  - It documents capacity where people look for it.
  - Third-party encodings state theirs the same way.
  - It gives `comline inspect` headroom to show, and runtimes a bound for
    requests in flight.
- **Against:**
  - Every limit needs vectors.
  - For the official datagram framings, the caps equal core's, so stating them
    adds rows without adding checks until a narrower encoding exists.
  - The build has to take the smallest of several caps.

Recommended, on the rule in [What stays out](#what-stays-out): **only the
caps the encoding's bytes impose**. Without that rule, limits become a place
where runtime, transport and schema limits blur together.

## Where they live

As for the existing facts:

- **Profiles:** each profile in the runtime's corpus gains the new facts, each
  value proven by vectors. Examples: `protocols = by_index` by a request
  addressing a protocol by its position, and `packages = several` by a
  `comline@3` hello listing two packages whose protocols are both #0.
- **Core** keeps its pinned copy, drift-checked as today.
- **The catalog** in the [shared vocabulary](../shared-vocabulary/catalog.md)
  gets an entry per fact.
- **[Official encodings](../../reference/wire/official-encodings.md)**
  renders every fact, and the capabilities derived from them, from the
  profiles.

## Open questions

- **What IPC adds.** The `handles` fact and the `handles_per_frame` limit
  are adopted (2026-11-14, [above](#framing)). Platform framings need `calls = by_hash` (FIDL), `errors = in_result`
  (Binder, Mojo, FIDL) and `correlation = synchronous` (Binder). D-Bus,
  the first platform framing, addresses *instances*, which no fact covers yet.
  All of this is laid out in [IPC, Framings](../ipc.md#framings).
- ~~**Does `one_way` belong here?**~~ Decided: yes, as the `one_way` fact
  ([above](#framing)).
- **Error scope.** `errors = by_ordinal` counts within the error space of the
  schema that declares the protocol. Every official framing names the
  protocol in a reply or matches it by request id, so the space is always
  known. A framing that does neither could only carry one schema's errors,
  which may warrant a fact later.
