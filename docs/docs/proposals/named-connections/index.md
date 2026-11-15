# Named connections

Status: **draft** · nothing here is decided: every choice is an open question at the
[end of this page](#open-questions) · develops a point left unbuilt by
[Connections](../connections.md#several-protocols-on-one-connection) (the declared set of
protocols allowed together) · sits beside
[A dependency's protocols on a connection](../dependency-protocols/index.md), whose
Proposals A and C are accepted · three parts: this overview, [the options](options.md) and
[prior art](prior-art.md)

**The question.** A package gets exactly one connection: one `Services`, one
`ClientServices`, one `accept`, `serve` and `connect`, and one `Connection<T>`, however many
protocols it declares. **Should a package be able to declare several named sets of protocols,
each generating entry points of its own, or should "one package, one connection" stay the
rule, with a separate package for each application?** Either way has a cost, and this page
sets both out so the choice can be made.

"Named connection" is the provisional name used here. `group` is already taken, by
[dependency groups](../use-paths-and-groups/dependency-groups.md), so the feature needs
another word: see [the name](#open-questions).

## The problem, as framed

A package is one application's connection today. Two situations strain that:

- **Several applications on one schema.** A shop has a public API and an admin API; a game
  has server to client and server to worker. They share types, and often some protocols (a
  health check, say). Each application wants its own `serve` that provides its protocols and
  nothing else, and its own `connect`.
- **A subset of one application.** A test server, or a gateway, serves some of a package's
  protocols and not the rest.

Two answers pull in opposite directions:

1. **Group the protocols** so one ("mono") package can generate several connections.
2. **Keep one package per application.** An application is a package; what several of them
   share is a package they depend on. The cost is that there is no one package for more than
   one application.

Neither is assumed here. [Option 0](options.md#option-0-status-quo) is the second, with what
exists today.

## Where things stand

Each point below was checked against the docs and the generators' code and golden output.

- **One connection per package.** A package with a protocol on a connection gets one
  `Services`, one `ClientServices`, one `accept`, `serve` and `connect`, and the
  `Connection<T>`, `Framing` and `Format` they name, in `connection.rs` (TypeScript:
  `connection.ts`). See the [Rust](../../languages/rust/connections.md) and
  [TypeScript](../../languages/typescript/connections.md) guides. The generator models it as
  one `PackageConnection` per package (`generation/codegen/src/connections.rs`).
- **Every protocol must be wired.** `Services` has a field for every protocol the server
  provides, and `ClientServices` one for every protocol the dialling side provides, so
  leaving one out doesn't compile. `connect(transport, ClientServices { .. })` therefore
  makes the dialling side provide every client-provided protocol in the package, and `serve`
  every server-provided one.
- **A subset is wired by hand.** Serving only some protocols means opening a `Connection`
  yourself and calling `ChatDispatcher(..).provide_on(&mut conn)` for each, as the guide's
  [By hand](../../languages/rust/connections.md#by-hand) section shows. Under `comline@2`,
  the default, the generated `accept` and `connect` also run the package's generated Hello
  (marked `#[doc(hidden)]`) and keep the negotiated result in the connection's extensions,
  which the senders consult before each call. A connection opened some other way "has nothing
  to check against, and every call goes", in the generated code's own words.
- **The protocols on a connection must agree.** If those on connections differ in framing or
  handshake, no one connection carries them all: `Services`, `serve` and `connect` aren't
  generated, `comline generation` warns, and each protocol keeps its own dispatcher and
  sender. The format is the package's one `wire.format`, not a protocol's, so it can't
  differ; a JSON-RPC protocol is JSON by definition.
- **Wire numbers are per package.** Under the defaults (`datagram@3`, `comline@2`) a
  protocol's number comes from the package's history. Under `comline@1` with `datagram@2` it
  is the protocol's position among the package's protocols, and `CONNECTION_IR_HASH`
  digests every schema in the package. The `comline@2` code in the runtime doesn't read that
  hash; its Hello carries per-protocol lines and shape hashes instead.
- **`comline@2` already compares per protocol.** A protocol only one end has is
  `unknown_protocol`, refused on its own, and `scope = protocol` keeps a refusal to that
  protocol. With `scope = protocol`, a connection whose every protocol is refused is refused
  ([the handshake](../../reference/wire/handshakes/comline@2.md#what-decides)). The Hello
  the generator embeds lists the protocols on the package's connection and that connection's
  three encodings (`facts::hello`).
- **So a set changes no wire number and no handshake message.** Each protocol keeps its
  package number, line and shape hash. What changes is which protocols a given end's Hello
  lists, and which entry points the generators write. That is a generation and compiler
  concept, not a wire one, under `comline@2`.
- **The declared set was never built.** [Connections](../connections.md#several-protocols-on-one-connection),
  decision 2 (2026-10-20), says: "Which protocols a connection carries is negotiated at the
  handshake: whatever the client offers and the server accepts. A package can optionally
  declare the set allowed together, as a constraint." Its
  [What it touches](../connections.md#what-it-touches) lists "the optional declared set of
  protocols" under core, and [What's built](../connections.md#whats-built) doesn't include
  it. A search of core, generation, the two generators and the runtime finds no trace of it.
  This proposal develops it, and asks whether it is still a constraint or has become a
  grouping for code generation ([question 4](#open-questions)).
- **Proposals A and C are accepted.** [A](../dependency-protocols/multi-package-connection.md)
  (`comline@3`) puts several packages on one connection, a dependency's protocol joining by
  `use` when its framing, handshake and format match the connection's.
  [C](../dependency-protocols/connection-per-package.md) gives each package a connection of
  its own, for protocols that can't share one and for isolation. C is the "one package per
  application" model that [Option 0](options.md#option-0-status-quo) builds on.

## The options

All four are described, with what each generates and checks, on [the options page](options.md).

| | 0: status quo | 1: sets in the manifest | 2: sets in the IDL | 3: a world-like declaration |
| --- | --- | --- | --- | --- |
| In one line | one connection per package; separate applications are separate packages | a table beside `wire` lists protocols by path | a `connection` block, or an annotation on each protocol | a declaration that also names a dependency's protocols |
| Mono package for several applications | no | yes | yes | yes |
| A subset of one application | by hand, without the generated negotiation | a set of its own | a set of its own | a set of its own |
| Where it is declared | nowhere: it is the package boundary | `config.idp` (the package) or `comline.toml` (the consumer): [open](options.md#where-the-table-lives) | the `.ids` files, in the frozen IR | the `.ids` files, or the manifest |
| New compiler concept | none | a manifest key | a declaration kind (block) or a known annotation | a declaration kind, with direction |
| Frozen IR format | unchanged | unchanged if in `comline.toml`; if in `config.idp`, to be checked | block: a new unit kind; annotation: probably not, to be checked | a new unit kind |
| Dependency protocols in a set | joins by `use` under A, as accepted | not without A | not without A | named in the declaration, under A |
| Encodings checked | per package, as today | per set | per set | per set |
| Default output with nothing declared | today's | today's | today's | today's |
| Reuse of one protocol by two applications | in a shared package, served on its own connection (C) or joined (A) | listed in both sets | named in both sets | named in both worlds |
| Version covers | the package | the package's every set | the package's every set | the package's every set |

## How the options differ in what they ask of the user

- **Option 0** asks nothing of the tools and the cost lands on the schema's authors: a types
  package and one package per application, and shared protocols in a package of their own.
- **Option 1** is the smallest addition to the language: the `.ids` files don't change, and
  protocols stay where they are. The set is described away from the protocol.
- **Option 2** puts the set beside what it contains. A block lists the set in one place; an
  annotation sits on each protocol, in the style of `@provider`, `@framing` and
  `@handshake`, and a protocol's sets are read off the protocol.
- **Option 3** is the only one that can name a protocol from a dependency in the declaration
  itself. It leans on [Proposal A](../dependency-protocols/multi-package-connection.md)
  being built, and it touches A's accepted rule that `use` puts a protocol on the
  connection.

The options aren't exclusive. Option 1 or 2 could ship first, and a world-like form could
extend it later, or Option 0 could stay as the rule and nothing be added.

## Open questions

Nothing is decided; each of these is for the user to answer. The options page has the detail
behind each one.

1. **Which direction?** Option 0 (nothing added: one package per application, Proposal C's
   model), 1 (sets in the manifest, in either of its two places), 2 (a block or an
   annotation), 3 (a world-like declaration), or a sequence of them (for example, one of 1
   or 2 first, 3 later). And a smaller step that isn't in the list: let `Services` and
   `ClientServices` take a subset, by an explicit per-protocol opt-out, without any new
   declaration. Is that enough for the "subset of one application" case, which the sets
   would otherwise cover?
2. **What is it called?** `group` is taken. Candidates: *connection* (the page's provisional
   "named connection"; it matches `connection.rs` and the `Connection<T>` the set generates), *endpoint*, *world* (WIT's word,
   which fits Option 3 and brings WIT's meaning of imports and exports with it), *role*
   (fits "server to client" and "server to worker" and reads oddly for a public and an admin
   API), *surface*. And whether the keyword, the table key and the generated module share
   one word.
3. **Who owns the declaration: the package or its consumer?** `wire` and `handshake` are in
   `config.idp`, which is frozen, hashed and published. `comline.toml` is, in its own words,
   "consumer-owned", "never frozen, and never part of a published package", and the
   [wire defaults](../package-wire-defaults.md) proposal moved `default_framing` out of it
   because "the framing is part of the contract both peers build from, so the producer
   decides it". A set in `comline.toml` is then presentation, like a
   [dependency group](../use-paths-and-groups/dependency-groups.md), and each consumer could
   define its own; a set in `config.idp` or the IDL is part of the package's contract.
   Which is meant? (The idea was first put as a table "next to `wire`" in `comline.toml`; `wire` is in
   `config.idp`, so that placement can't be taken as written.)
4. **A grouping for code generation, or a constraint?** The Connections decision called the
   declared set "a constraint". Is a set only what a generated `serve` and `connect` take,
   or does something enforce it: a runtime refusing a request for a protocol outside the
   connection's set, a build error when a handler for a protocol outside the set is
   registered? Under `comline@2`, a peer outside the set is told `unknown_protocol` for each
   protocol it lacks; is that enough?
5. **What happens to the whole-package connection once sets are declared?** The default, with
   nothing declared, must stay exactly today's output. When sets are declared, does the
   unnamed connection (every protocol, as today) still exist beside them, or only the named
   ones? And a protocol that is in no set: an error, put in a default set, or left off every
   connection, as a protocol on `datagram@1` is today?
6. **May a protocol be in more than one set?** A health check in every application's set is
   the case for it. The case against is that two sets then provide the same dispatcher and a
   reader can't tell from a protocol which connections it is on.
7. **What does a set say about encodings?** Framing and handshake are per protocol today
   (`@framing`, `@handshake`) and checked to agree across a package's connection; the format
   is the package's. With sets, the framing and handshake check applies per set, so two sets
   can differ. Should a set be able to state its own `wire` and `handshake`, and, if so, its
   own format, which today isn't a per-protocol or IR fact?
8. **May a set name a dependency's protocol, and when?** Only once `comline@3` exists (A),
   and with all three encodings matching, as A decided? Or also under `comline@2`, where
   step 0 leaves a dependency's protocols off the connection? If a set names one, does `use`
   still put a protocol on the connection by itself, or does the set replace `use` as the
   reach (a change to an accepted point of A)? When the encodings differ, is the error the
   one A gives, pointing to a connection of its own (C)?
9. **How do versions treat sets?** The package version still covers every set, since lines
   and shape hashes are per protocol. Is adding a set, or a protocol to a set, a minor
   change, and removing one a major change, by analogy with how A treats a dependency's
   protocol joining the connection? Is a rename of a set breaking, since it renames
   generated code? Or does a set not move the version at all, as with groups?
10. **What does a set's Hello list?** Today the generated Hello lists every protocol on the
    package's connection. A set's Hello listing only its members is honest to the peer (it
    sees `unknown_protocol` for the rest, and calls to them fail locally, as `Unavailable`),
    and differs from a package whose subset is wired by hand. Is that the intended behaviour?
11. **Do sets reach `comline@1` and `datagram@2`?** Under them, numbers are positions among
    the package's protocols, and the hash digests every schema, so a change in one set
    refuses connections in every set. Options: restrict sets to `datagram@3` with
    `comline@2` and later; keep the positions, with a hash per set; or the whole-package hash
    as today.
12. **What does the generated code look like?** A module per set (`connection::admin::{Services, serve, connect, Connection, Framing, Format}`),
    or prefixed names (`AdminServices`, `admin_serve`) at the same level; in `lib` mode,
    whether a set's items are re-exported at the crate root; in `code` mode, the file for a
    set and how the `layout` template names it; and TypeScript's form (a file per set, or a
    namespace in `connection.ts`). Which names are reserved: a set called `connection`, or
    named like a schema, as a schema named `connection` can't be used in `code` mode today.
13. **Do JSON-RPC and `async` go per set?** For JSON-RPC, once one JSON-RPC protocol in a
    package is client-provided, all of them share the connection, and the bare-name
    collision check runs over that one connection. Per set, both would apply within the set.
    `async` is `comline.toml`'s `[generate]` key, a setting for the whole target; does it
    stay so?
14. **For Option 3, where does direction live?** A protocol's side is `@provider` today
    (`Server`, `Client` or `Multiple`) and `Services` and `ClientServices` follow from it. A
    world-like declaration could say which side provides each member instead. Does the
    declaration replace `@provider`, sit beside it with the two checked against each other,
    or leave direction on the protocol?
15. **Order of work and where it ships.** The specification's conformance cases first (the
    house order for a compiler rule), then core, generation and the generators, the CLI and
    language server, and the docs. Does any of it wait for `comline@3`, and does it ship as
    a draft behind a switch, or not until the questions above are answered?

## What it touches

Nothing is built; this lists where each option would reach.

- **core:** the declaration (a manifest key, a block, or an annotation), its parsing and
  validation, the encoding check applied per set (the compiler's check of which encodings may
  share a connection isn't built yet, so a set is part of its design), the frozen IR if the
  declaration is in the IDL (a change under the
  [IR migrations](../ir-migrations/index.md) framework if it adds a unit kind), the facts
  and the version rules for a set, and the diagnostics. Whether the package's
  `config.idp` grammar can hold it: its values have no list form, only strings, numbers,
  names and dictionaries.
- **specification:** compiler cases for the new errors and the unchanged default output,
  catalog entries for the diagnostic codes
  ([shared vocabulary](../shared-vocabulary/index.md)), and generator conformance output for
  a package with sets.
- **generation:** `PackageConnection` becomes a set of them; `package_connection_among`,
  `check` and `hello` run per set; the request carries the sets, additively, as
  `dependencies` was added, so a request without them is today's; the JSON-RPC and
  bare-name checks scope to a set; warnings name the set.
- **comline-rust and comline-typescript:** `connection.rs` and `connection.ts` emit one block
  per set, and the golden outputs gain a case for sets, and the default's stay as they are.
- **runtime:** none under `comline@2`: the handshake, framing and `Connection` are unchanged,
  and only the embedded Hello differs per set. Under `comline@1`, the hash passed to
  `accept` and `connect` could be per set (question 11).
- **cli:** `comline generation` and `comline inspect` show the sets, and
  `comline inspect` is the place for what a set carries (A has that open already).
- **language-server:** completion, hover, go to definition and diagnostics for the
  declaration, and for each set's members.
- **docs:** the Rust and TypeScript connections guides, the
  [packages guide](../../guides/packages/index.md), the
  [`config.idp`](../../reference/package/idp.md) or
  [`comline.toml`](../../reference/package/comline-toml.md) reference (and its JSON Schema),
  the [`comline@2`](../../reference/wire/handshakes/comline@2.md) page on what a Hello
  lists, and this proposal's status.
