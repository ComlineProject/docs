# Language Implementation

## Who maintains a language

!!! note "Context"
    A language in this context means maintenance of a language compatibility for Comline, which involves: runtime, generator, conformance, facts, fuzzing, benchmarks.

There is no named maintainer per language today — the project is set up so
that doesn't become a single point of failure as more languages (and more
people) show up. Each language's generator and runtime live together in
that language's own repo under the `ComlineProject` GitHub org, which holds
the published-package namespace (the npm scope, the future crates.io name,
and so on for later languages). A contributor gets *publish rights*, not
ownership of the name — releases run through CI trusted publishing (OIDC),
not a personal token, so one maintainer stepping away never orphans a
published package.

The full reasoning is in [Runtime & generation repo
structure](../../design/runtime-repo-structure.md#ownership-packaging) if
you want the detail; this page just needed to say it exists.

## How is a language mantained

Test