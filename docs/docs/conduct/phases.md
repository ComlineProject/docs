# Phases and promises

What Comline promises, and when. Decided 2026-10-27.

## Phases

- **Early days,** which is now.
- **Previews,** smaller announcements before 1.0. Still early days.
- **The 1.0 announcement,** which is what sets stability.

## Always

- Correctness, conformance, performance and safety are never lowered.
- The [branch rules](branch-rules.md) and required checks apply.
- A change to wire behaviour comes with conformance vectors, and every
  runtime passes them.

## Early days

Until the 1.0 announcement.

- Every version is `0.x`.
- Anything may break:
  - APIs and generated code;
  - the C ABI, where a minor bump counts as breaking;
  - the IR and config formats.
- Wire formats (`packed@1`, `datagram@2`, `jsonrpc@1`, `comline@1`) may change
  their bytes in place, but only in one cascade:
  - the vectors change;
  - every runtime (Rust, TypeScript, the simulator) passes them;
  - all of it before anything merges.
- No deprecation periods.
- Everything is consumed by git revision, with pins such as `VECTORS_REV` and
  the comline-core revision.
- No registry publishing, no release workflow, no prebuilt binaries.
- Proposals may still change.

## Previews

- Smaller announcements before 1.0.
- They keep the early-days rules and say so: `0.x`, breaks allowed.

## From the 1.0 announcement

- Semver: a break needs a major version.
- Anything users rely on is marked deprecated, with its replacement already
  available, in at least one minor release before the major that removes it.
  The changelog says so both times.
- A wire format's bytes never change again. A change is a new `@N`.
- The C ABI's structs are frozen within a major. Status codes and flags are
  append-only.
- Packages go to registries (npm, crates.io, …) under ComlineProject-owned
  names.
  - Published from CI with trusted publishing (OIDC), no long-lived tokens.
  - Reproducible builds, with published checksums.
  - Inter-repo development may keep using git revisions.
- Background: [Ownership & packaging](../design/runtime-repo-structure.md#ownership-packaging).
