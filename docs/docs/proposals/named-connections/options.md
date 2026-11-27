# Named connections: the options

Status: **draft** · nothing here is decided · part of
[Named connections](index.md), which has the question, the open questions and what it
touches

Each option is described with the same headings: what it is, what is generated, what core
checks, how it versions, what it costs the tools, and how a package gets there. The names
(`connection`, `admin`) and the syntax are illustrative, not proposed.

The example used throughout is a shop package with a public API and an admin API that share a
health check:

```ids
// shop/chat.ids, shop/admin.ids, shop/health.ids (protocols only, shortened)
protocol Orders { function place(order: Order) -> OrderId; }
protocol Admin  { function refund(id: OrderId); }
protocol Health { function ping(); }
```

Today `serve` and `connect` for that package take every protocol, so a process that should
serve only the public API either provides `Admin` too or wires its connection by hand.

## What every option shares

These hold whichever option is taken, and aren't repeated below.

- **No wire number moves.** A protocol keeps its package's number, line and shape hash in
  every set it is in. A peer built from the package with no sets, and a peer built with sets,
  compare protocol by protocol as `comline@2` does today.
- **A set is a connection.** It has its own `accept`, `serve`, `connect`, `Services`,
  `ClientServices`, `Connection<T>`, `Framing` and `Format`, written from the protocols it
  lists, on the framing and handshake they share. What is generated for the whole package
  today is what a set with every protocol would generate.
- **The default stays as it is.** A package that declares nothing gets exactly today's output,
  file for file. The generators' golden outputs for it don't change.
- **Two ends needn't pick the same set.** A client built for `public` and a server serving
  `admin` share the protocols they both list, and `unknown_protocol` refuses the rest. If
  they share none, the connection is refused under `scope = protocol` (the whole connection
  when every protocol is refused), so dialling the wrong set fails at the handshake instead of
  at the first call.
- **The version is the package's.** There is one package version, and lines and shape hashes
  stay per protocol, so every set is covered by it ([versioning](#versioning-in-every-option)).

## Option 0: status quo

**What it is.** A package has one connection. Several applications are several packages, and
what they share is a package they depend on. This is
[Proposal C's](../dependency-protocols/connection-per-package.md) model applied to one
organisation's own schemas rather than to a library's.

```text
shop-types      types and the shared Health protocol
shop-public     depends on shop-types; protocol Orders       one connection: Services { orders }
shop-admin      depends on shop-types; protocol Admin        one connection: Services { admin }
```

**What is generated.** Exactly today's: each package's own `connection.rs`. `Health` lives in
`shop-types`, so a consumer reaches it by `use` under
[Proposal A](../dependency-protocols/multi-package-connection.md) (one connection, when the
encodings match), or serves it on `shop-types`' own connection (C).

**What core checks.** Nothing new.

**For.**

- Nothing to build, and one identity per protocol, checked against its own package's version.
- Each application's version moves only with its own changes.
- Isolation by construction: a package's connection state, handlers and refusals are its own.

**Against.**

- No mono package for more than one application. A repository with a public and an admin
  application is two or three packages, and each needs its own `id`, version history and
  releases.
- A protocol both applications use belongs to a third package, and until Proposal A is built,
  a dependency's protocols stay off the consumer's connection (step 0), so the application
  serves `Health` on a second connection.
- A subset of one package still means wiring by hand, without the generated negotiation.
- Moving a protocol between applications is a removal from one package and an addition to
  another, each with its own version and consumers.

**Smaller steps that stay in Option 0.** Not proposed, listed because they might be enough for
part of the problem ([question 1](index.md#open-questions)): letting `Services` and
`ClientServices` take a subset through an explicit per-protocol opt-out, which would answer
"a subset of one application" without any declaration of a set.

## Option 1: sets declared in the manifest

**What it is.** A table lists named sets of protocols by path. The `.ids` files don't change.

### Where the table lives

The two places have different consequences, so which one is meant is
[question 3](index.md#open-questions).

- **In `config.idp`, beside `wire` and `handshake`.** It is the package's: frozen, hashed and
  published, so a consumer sees the sets the author declared. The manifest grammar has no list
  value (strings, integers, booleans, names and dictionaries), so protocols would be keys of a
  dictionary, as `code_generation.languages` is, or the grammar would gain a list:

  ```idp
  connections = {
      public = { protocols = { shop::orders::Orders = {} shop::health::Health = {} } }
      admin  = { protocols = { shop::admin::Admin = {} shop::health::Health = {} } }
  }
  ```

- **In `comline.toml`.** It is the consumer's: "never frozen, and never part of a published
  package". `comline.toml` takes lists, and `[[generate.target]]` already has the shape
  of a repeated table:

  ```toml
  [[generate.connection]]
  name      = "admin"
  protocols = ["shop::admin::Admin", "shop::health::Health"]
  ```

  A set here is a filter on what to generate. Each consumer chooses its own sets, a set can't
  be part of the package's contract, and the package's author can't document "the admin
  connection" as a thing a consumer can rely on. `comline.toml` also has a JSON Schema that
  would gain the key.

**What is generated.** A module per set beside today's items, for example:

```rust
// Rust, lib mode
use shop::connection::admin::{serve, Services};            // admin's own
serve(transport, Services { admin: AdminImpl, health: HealthImpl })?;

use shop::connection::public::connect;                      // public's own, ClientServices if any
let mut conn = connect(transport)?;
```

```ts
// TypeScript
import { admin } from "shop";                               // illustrative
await admin.serve(transport, { admin: adminImpl, health: healthImpl });
```

Each set's `Services` has a field per protocol the server provides in that set and
`ClientServices` one per protocol the dialling side provides in it, so leaving one out still
doesn't compile. Under `comline@2` each set embeds its own Hello, listing only its protocols
and its encodings. [Question 12](index.md#open-questions) is the naming and layout.

**What core checks.**

- Every path names a protocol the package declares (or, under A, reaches).
- A set's name is unique, a valid identifier, and not reserved.
- The encodings agree per set: its protocols share a framing and a handshake, as a package's
  must today. A disagreement names the set and both protocols.
- Whether a protocol may be in no set, or in several: [questions 5 and 6](index.md#open-questions).
- A set naming a protocol that isn't on a connection at all, such as a server-only protocol
  on `datagram@1`, is an error.

**Versioning.** A table in `config.idp` is part of the package and the frozen config, so
changing it needs a rule ([versioning](#versioning-in-every-option)). In `comline.toml` it
moves no hash and no version, like a [group](../use-paths-and-groups/dependency-groups.md).

**Tools.**

- **Language server:** the manifest, if it holds a set, is a file with a schema of its own in
  the editor: completion for protocol paths, diagnostics for a path that doesn't resolve.
- **CLI:** `comline generation` writes the sets; `comline inspect` lists them.
- **Spec:** compiler cases for the table and its errors.

**Migration.** Nothing changes for a package without the table. Adding it adds modules; the
root items stay unless [question 5](index.md#open-questions) is answered the other way.

**For.** The smallest change to the language, none to the `.ids` files. If it lives in
`comline.toml`, none to the frozen IR or the compatibility rules either.

**Against.** The set is declared away from the protocols it lists, so a protocol's page
doesn't say which connections it is on. Paths in a manifest can go stale when a protocol is
renamed, and the manifest grammar needs a way to write them.

## Option 2: sets declared in the IDL

**What it is.** The `.ids` files say which protocols are in which set. Two forms.

### 2a: a block

```ids
connection Public {
    Orders
    Health
}

connection Admin {
    Admin
    Health
}
```

The block names protocols by the same paths `use` takes. It is a new declaration kind, so the
frozen IR gains a unit kind: a change under the [IR migrations](../ir-migrations/index.md)
framework, with a frozen copy of the format, a migration step and its fixtures.

### 2b: an annotation on each protocol

```ids
@connection = [public, admin]
protocol Health { function ping(); }

@connection = admin
protocol Admin { function refund(id: OrderId); }
```

(The list value is illustrative; whether an annotation takes one is part of the design.) This is in the style of `@provider`, `@framing` and `@handshake`: they are protocol
annotations that core already writes into each protocol's parameters, where the generator
reads them (`Provider::of(parameters)` and `framing(parameters)`). A new known annotation
probably needs no new unit kind; that is to be checked against the format document. A
protocol's sets read off the protocol, and the set's membership is spread across the files
where the protocols are.

**What is generated, what core checks, versioning, tools.** As Option 1, with these
differences:

- **Resolution.** Block members are paths resolved like a `use`, which makes them subject to
  the [own-schema path rules](../use-paths-and-groups/relative-use.md) (`package::`,
  `parent::`, `self::`). An annotation names a set by a string and resolves nothing.
- **In the IR, so in the history.** The set is part of the frozen IR from the first build, so
  `comline build` records it, and a version diff sees a protocol move between sets.
- **The language server** gains block completion, go to definition from a set to its members,
  and hover on a protocol listing its sets.
- **Spec:** parser cases for the declaration, compiler cases for the errors, and a catalog
  entry for each new diagnostic.

**Migration.** A package without the declaration builds as before. A package that adds the
annotation to some protocols and not others needs a rule for the rest
([question 5](index.md#open-questions)).

**For.** The declaration is where the protocol is (2b) or in one place in the schema (2a),
checked by the compiler with the rest, recorded in the history, and visible to every tool that
reads the IR.

**Against.** A language change, and for 2a an IR format change. For 2b, a set's list of
members exists nowhere as one thing: finding "what is in `admin`" means reading the
annotations.

## Option 3: a world-like declaration

**What it is.** A declaration lists what a connection provides and consumes, and may name
protocols of other packages, after WebAssembly's WIT `world`
([prior art](prior-art.md#webassembly-wit-worlds)):

```ids
connection Admin {
    provide   Admin
    provide   Health
    provide   localdeps::greeting::Foo      // a dependency's protocol, under Proposal A
    consume   AuditEvents
}
```

It differs from Options 1 and 2 in two ways.

- **It names the protocols of dependencies in one place.** Under
  [Proposal A](../dependency-protocols/multi-package-connection.md), which dependency
  protocols join a connection is decided by `use`, a reach put on the whole package. A
  declaration naming them gives a set its own reach. That is a change to an accepted point of
  A (that `use` of a protocol puts it on the connection) unless the two are kept together
  ([question 8](index.md#open-questions)). It depends on `comline@3` being built: under
  `comline@2`, step 0 keeps a dependency's protocols off a package's connection, so there
  would be nothing to name.
- **It carries direction.** `provide` and `consume` say which side implements a protocol, which
  today `@provider` on the protocol states for every connection the protocol is on, and
  which `Services` and `ClientServices` follow from. Whether the declaration replaces
  `@provider`, sits beside it, or leaves it ([question 14](index.md#open-questions)).

**What is generated.** As Options 1 and 2, and the generated modules of dependency protocols
are reused: a set that names `localdeps::greeting::Foo` uses the dependency's own dispatcher
and sender, which generation already emits as the package's own for each dependency schema.
WIT's `wit-bindgen` has a `with` option for the same thing: point at already-generated
bindings rather than regenerate them.

**What core checks.** As Options 1 and 2, and:

- The three encodings of a dependency's protocol match the set's, by parameter hash in its
  facts, as A requires; otherwise the error points to a connection of its own (C).
- One version per package per end: if a set reaches a dependency by two paths with different
  pinned versions, it is refused, as in A.
- Direction agrees with `@provider`, if both are written.

**Versioning.** As Options 1 and 2. A set that names a dependency's protocol is also subject
to A's rule that the consumer's version covers which protocols its connection carries: adding
one is minor and removing one is major, as A has it for the whole connection.

**Tools.** As Option 2, plus `comline generation` reading a dependency's facts for the
protocols a set names (which A already requires of the CLI), and `comline inspect` showing the
packages in each set.

**Migration.** A package without the declaration builds as before; `use` keeps working under
A if the two are kept together.

**For.** One place says everything about a connection: what it provides, what it consumes and
whose protocols it carries. It is the form with the most prior art, and the one that extends
to dependencies.

**Against.** The largest language change of the four, a second place to say direction, and a
dependency on `comline@3`. A set that is only "which of my own protocols" has no use for it.

## Versioning in every option

The package version covers every set, because the comparison is per protocol and a set
doesn't change a protocol's number, line or shape hash. What is left to decide is whether the
*declaration* of a set is itself a change, and of what size ([question 9](index.md#open-questions)).
Rules from elsewhere in the docs that this would follow or depart from:

| Change | By analogy with | Would be |
| --- | --- | --- |
| a protocol added to a set | a dependency's protocol joining the connection (A): minor | minor |
| a protocol removed from a set | the same: major | major |
| a set added | a function added: minor | minor |
| a set removed or renamed | a protocol removed: major | major |
| any of these, in `comline.toml` | a dependency group: moves no hash | none |

These rows are analogies, not proposals. The `comline.toml` row holds only where the table is
the consumer's (Option 1's second place).

## What is generated, at a glance

| | No sets declared | A set `admin` |
| --- | --- | --- |
| Rust | `connection.rs` with `Services`, `ClientServices`, `accept`, `serve`, `connect`, `Connection<T>`, `Framing`, `Format` | the same items, per set, in a module or under prefixed names ([question 12](index.md#open-questions)) |
| TypeScript | `connection.ts` with the same | the same, per set |
| Hello (`comline@2`) | every protocol on the package's connection | the set's protocols only |
| `comline@1` hash | every schema in the package | whole package, or per set ([question 11](index.md#open-questions)) |
| JSON-RPC | the package-wide rule | the rule, per set ([question 13](index.md#open-questions)) |
