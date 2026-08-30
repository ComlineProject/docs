# IR freezing & the version state

`comline build` lowers each schema to its
[Intermediate Representation](../guide/ir/index.md) and **freezes** it: the IR
units are written into the project's
[content-addressable store](../guide/ir/cas.md) at `.comline/`, as one immutable
commit in an append-only chain. That store *is* the version state — there is no
separate lockfile. (An early `state.lock` idea was dropped before it was built;
the CAS covers what it was meant to.)

Each build diffs the new frozen units against the previous commit, records the
differential changes, and uses the largest of them to bump the package version.

## Version state

Versioning follows SemVer. The first sketch of the rules here was only "new
field → minor, changed field → major"; the implemented rules are richer and
cover frozen-config changes too. The current table lives in
[Versioning rules](../reference/versioning.md).

## Components

A *component* is any part of a schema that declares something:

- namespace
- constant
- settings
- structure
- enum
- error
- validator
- protocol

## The `clean` / `reset` split

`comline clean` used to delete `.comline/` outright, together with generated
code — one unguarded verb over two very different things: regenerable output and
the irreplaceable version history (nothing else holds it; there is no `publish`
yet). Landed in `ComlineProject/cli` #15:

- **`comline clean`** — removes only generated code. `.comline/` is never
  touched.
- **`comline reset`** — deletes `.comline/` *and* generated code. On a terminal
  it shows how many versions will be lost and requires typing `reset`; without a
  terminal it refuses (exit `2`) unless `--force`. `--dry-run` on either lists
  without deleting.

## Reproducibility

The CAS covers version history and diff-driven auto-versioning, but not yet a
fully reproducible rebuild — imported and dependency schemas are not pinned into
the commit. See the
[CAS reproducibility gap](consumer-generation-config.md#related-cas-reproducibility-gap).
