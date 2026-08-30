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

## `comline clean` is destructive

Today `comline clean` deletes `.comline/` outright, together with generated
code. Nothing else holds the history and there is no `publish` yet, so the next
build starts over at `0.0.1` with no way back.

That conflates two very different things — regenerable output and the
irreplaceable version history — under one unguarded verb. The intended split:

- **`comline generate --clean`** (or `comline generate clean`) — removes only
  generated code. Safe; no confirmation needed, or an opt-out `--yes`.
- **`comline reset`** — deletes `.comline/`. Requires an explicit confirmation
  (type the package name, or `--force`). It exists so "start the version history
  over" during pre-1.0 churn is a sanctioned move rather than a manual
  `rm -rf .comline`.

`comline clean` itself would then either alias `generate --clean` or be removed.

## Reproducibility

The CAS covers version history and diff-driven auto-versioning, but not yet a
fully reproducible rebuild — imported and dependency schemas are not pinned into
the commit. See the
[CAS reproducibility gap](consumer-generation-config.md#related-cas-reproducibility-gap).
