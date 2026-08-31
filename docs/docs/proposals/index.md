# Proposals

Ideas for the project from authors and contributors, triaged for fit. A proposal
captures a direction and its trade-offs. Once the team commits to one, the
rationale and rollout move to a [Design](../design/index.md) record and the
proposal is marked **accepted**.

## How a proposal is written

Each page opens with a `Status:` line, house style — a status in bold followed by
` · `-separated notes:

- **draft** — being written, not yet up for discussion
- **under discussion** — open for feedback
- **accepted** — the team is going this way; see the linked Design record
- **rejected** / **superseded** — with a note saying why, and by what

Proposals may **compete**: two pages proposing different answers to the same
question. They are grouped together below and stay open until one is accepted;
the others become rejected or superseded with a one-line reason.

## By area

### [Runtime & codegen repository organization](repo-organization/index.md)

How the per-language surface — codegen, libgen, runtime — is split across
repositories. Two competing proposals, read to the same shape:

- [Proposal B — split by language](repo-organization/split-by-language.md) — one
  repo per target holds that language's codegen, libgen, and runtime together.
  ***accepted*** — adopted directly by the design record.
- [Proposal A — split by concern](repo-organization/split-by-concern.md) —
  `generation` stays one repo; `runtime` graduates heavyweight language runtimes
  to their own repos. *rejected — superseded by B; kept for the reasoning.*

Org-wide decision record:
[Design → Runtime & generation repository structure](../design/runtime-repo-structure.md).

### Tooling

- [Automatic documentation](auto-documentation.md) — derive human-readable docs
  from the schema and project files, as an optional tool. *draft.*
