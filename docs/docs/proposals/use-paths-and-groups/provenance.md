# Provenance, not names

Status: **accepted** · decided with the user 2026-11-15 · part of [Own schemas, provenance and
dependency groups](index.md) · needs an IR format bump under [core#268](https://github.com/ComlineProject/core/issues/268)

**The question.** Whether a compiled schema is the package's own, a dependency's or `std`'s decides what is done with
its protocols: whether they get wire numbers, whether they are on the package's connection, whether a comparison goes
by what they declare or by what the package reaches. **Can that be a recorded fact instead of something every tool
infers from how a namespace is spelled?**

## Where things stand

A dependency's schemas are compiled in their own package and brought in as they were frozen, with their namespace
prefixed by the name the consumer gave the dependency (`package::deps::resolve`: `shared_types`'s `src/foo.ids` is
`shared_types::foo`). `std`'s schemas sit under `std`. Nothing else says where a schema came from. So:

| Who | How it tells a dependency's schema from the package's |
|---|---|
| core, the stored version history | the first segment of the namespace is in `compat::dependency_names`: the `dep_<name>` entries of the version's tree (`compat::vendored`), plus `std`. `Loaded::of` and the build's comparison each do this split |
| core, `inspect` and `doc` | by the stored `dependency_configs` |
| generation | `connections::is_dependency`: `std`, or a namespace whose first segment is one of `GenerateRequest::dependencies`, mirrored from core because `compat` is behind a feature the codegen crate doesn't enable |
| core's shadowing guard | refuses a package's own schema named like a dependency or `std` |

The same rule written three times, and each can only be right while no schema of the package is spelled like a
dependency's.

There is a second, plainer disagreement. Core's compiled namespaces are `::`-joined (`localdeps::greeting`); a
generation request's are `/`-joined (`localdeps/greeting`). A comparison of the two forms failed for nested schemas, and
was fixed separately. That the fix had to be made is part of the case here: two forms of one name, compared as text.

## The change

**Decided.** Each compiled schema **records the package it came from**: one of

- the package itself,
- a named dependency (the name the package gives it), or
- `std`.

The record is carried in:

- **the frozen IR**, with the schema, so a stored version says it, and a version history read years later doesn't depend
  on the spelling rules of the core that reads it;
- **the generation request**, with each schema, replacing the list of dependency names the request carries today
  ([generation#146](https://github.com/ComlineProject/generation/pull/146)): `is_dependency` and `reached` read it;
- **the facts**, per protocol, so that [reach and per-package numbers](https://github.com/ComlineProject/core/issues/277)
  are recorded against the package a protocol belongs to and not against a name.

Nothing infers "dependency" from a namespace's spelling any more. `compat::dependency_names` and `compat::vendored`
stop being a classifier: the `dep_<name>` entries remain how a version *stores* what it vendored, and nothing else.

A dependency's schemas keep their namespace prefix: it is how `use greeting::hello::X` reads and how the generated
files are laid out. What changes is that the prefix no longer decides anything.

### One canonical namespace

A namespace is compared as its segments, never as two strings joined differently, and requests and facts use one form.
Core's IR is frozen with `::`, so the request and the facts take that; where a generator needs a path (`/`, for a file),
it makes it from the segments. The spelling is settled where the request type changes, in generation.

## Which format

This is a change to what a version freezes, so the format stamp moves and there is a step for it under
[IR migrations](../ir-migrations/index.md): frozen copies of the formats, an `up` that writes what the old format never
recorded (as known where it can be shown, explicit unknown where it can't), an inverse witness, fixtures, a format
document, all in one pull request, or the gate fails. The question is *which* format.

The first migration step, [3 to 4](../ir-migrations/format-4.md), is the chains of
[granular `@unverified`](../shared-vocabulary/granular-unverified.md) ([core#222](https://github.com/ComlineProject/core/issues/222)),
and is the first real client of the system.

| | Rides with format 4 | Comes right after, as format 5 |
|---|---|---|
| **Bumps** | one: a store is migrated once | two: the first migration, then another; a store written by 3's closing core goes 3 to 4 to 5 |
| **The step** | the 3-to-4 step also writes provenance | a small step of its own, `up` writing provenance from the old rule |
| **What `up` writes** | provenance from the `dep_<name>` entries and the namespace rule. That rule is the old classification, and exact for any version built since the shadowing guard ([#256](https://github.com/ComlineProject/core/pull/256)): the guard is what made the spelling a true record. For an older store it may be wrong, which the step would mark unknown instead | the same |
| **Risk to the first client** | format 4's pull request grows, and #222's chains and provenance have to be reviewed, proven and fixtured together, in the first real use of the system | format 4 is as designed; provenance gets its own fixtures and its own square |
| **Hashes** | moved once: every object's address, a dependency pin and `schema_ir_hash` change at the same bump | moved twice |
| **Timing** | provenance waits for #222, or #222 waits for it | independent; provenance can ship after 4, and the rest of this proposal doesn't wait on the IR |

**Decided: either.** It rides with format 4 if both are ready together, and is format 5 otherwise. Whichever it is, the 1.0 reset applies: stores in today's
formats aren't migrated, and only the format that exists at 1.0 carries a guaranteed path.

## What the guard becomes

The shadowing guard exists because classification was by name. With provenance recorded, and an own schema reachable only
as `package::…`, a package's own `greeting` and a dependency's `greeting` can no longer be confused by a `use`, or by a
tool.

They can still *land on the same compiled namespace*: an own `src/greeting/hello.ids` and the dependency's `hello.ids`
are both `greeting::hello`, and two files cannot be generated at one path
(`{{language}}/{{namespace}}.{{ext}}`). So the guard doesn't simply go.

**Decided: the guard stays as it is.** A package's own schema named like a dependency, or `std`, is still refused. It
no longer protects classification, which provenance does, but it keeps every compiled namespace, and every generated
file, unique, with the message it has today. Narrowing it to equal namespaces, or prefixing a dependency's output, was
considered and not taken: either lets a package's own `greeting` sit beside a dependency `greeting`, which a reader of
the generated code would confuse as easily as the tools once did.
