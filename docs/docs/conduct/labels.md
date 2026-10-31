# Labels

The labels every ComlineProject repository uses on issues and pull requests.
One set, defined in
[`labels.yml`](https://github.com/ComlineProject/docs/blob/main/labels.yml) in
the `docs` repository.

## Keeping them in step

- `scripts/sync-labels.sh` reads `labels.yml` and creates or updates each
  label in every repository that isn't archived.
- It never deletes a label. `--prune` also deletes labels that aren't in
  `labels.yml`.
- To change a label, change `labels.yml` in a pull request, then run the
  script.

## Priority

At most one per open issue. Priorities are set by the maintainer.

- `P0`: now, top priority.
- `P1`: next.
- `P2`: soon.
- `P3`: eventually.
- `later`: parked. Kept for the record, not planned.
- No priority label means it hasn't been looked at, or it is a tracking
  issue.

## Type

What kind of issue it is.

- `bug`: something isn't working.
- `enhancement`: a new feature or a request.
- `design`: needs a decision before anyone builds it.
- `question`: further information is requested.
- `documentation`: docs to write or fix.
- `chore`: maintenance, cleanup, quality.
- `breaking-change`: breaks an API, generated code or wire bytes.

## Status

- `1.0-blocker`: must be done before the 1.0 announcement. The list is
  [Ready for 1.0](readiness.md). Every blocker is in its repository's `1.0`
  milestone.
- `blocked`: waiting on something else. Say what in a comment.

## Areas

What part of Comline the issue touches. An issue can have several.

- `wire`: formats, framings, handshakes.
- `compiler`: parser, IR, CAS.
- `config`: packages, `config.idp`, settings.
- `codegen`: code generation.
- `runtime`: runtimes and the shared core.
- `tooling`: CLI, language server, editor.
- `playground`: playground and simulator.
- `stdlib`: standard library.
- `versioning`: versions and compatibility.
- `extensibility`: third-party encodings and generators.
- `testing`: tests, fuzzing, conformance.
- `diagnostics`: errors and diagnostics.
- `performance`: speed and size.
- `security`: security and safety.

## GitHub's defaults

- `duplicate`, `invalid`, `wontfix`, `good first issue` and `help wanted` are
  kept as GitHub makes them.

## The project board

- The [Comline Development Roadmap](https://github.com/orgs/ComlineProject/projects/2)
  reads priority, area and 1.0 blocker from these labels.
- Change the label, not the board's field, when they disagree.
