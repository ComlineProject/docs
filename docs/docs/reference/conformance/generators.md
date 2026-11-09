# Generator conformance

How each code generator's output is pinned, and how its feature support is
proven. The source of truth is the generation repository's
[`conformance/README.md`](https://github.com/ComlineProject/generation/blob/master/conformance/README.md).

## Flow

1. **Fixtures.** Each fixture in `conformance/src/lib.rs` is one schema as
   hand-built IR (`Vec<FrozenUnit>`), not parsed source. The corpus pins IR
   shape, not parser behaviour.
2. **Goldens.** Every registered generator runs over every fixture, and its
   output is diffed against `tests/golden/<fixture>/<lang>.<ext>`. A golden is
   a snapshot of what the generator does now, not what it should do: a change
   in output shows up in that pull request's diff and is re-blessed
   deliberately.
3. **Support claims.** Each generator states what it implements in its
   `SUPPORT` table (`comline_codegen::features`). `support_is_proven` checks
   every claim against the fixtures.
4. **Outputs.** The proven table is written to `FEATURES.md` and
   `features.json` at the repository root, by the same run that blesses the
   goldens.
5. **Consumers.** The [Languages](../languages/index.md) pages and the
   [Observatory](reports.md)'s `codegen` matrix read `features.json` from the
   default branch.

```sh
cargo test -p comline-conformance                     # check
CONFORMANCE_BLESS=1 cargo test -p comline-conformance  # regenerate goldens and FEATURES
```

## Support claims

| Claim | Holds when |
| --- | --- |
| `supported`, `partial` | a fixture uses the feature, generates, and matches its golden; where the feature can be taken out, the output differs without it |
| `ignored` | the output is exactly what it would be without the feature |
| `unsupported` | generation is refused, with an error naming the feature |

A claim no fixture can back fails the suite, so a new feature comes with a
fixture.

## When it runs

| Where | When | Checks |
| --- | --- | --- |
| generation | every pull request and push (`cargo test`) | goldens match; every claim is proven; `FEATURES.md` and `features.json` are current |
| docs | weekly (`language-support-drift.yml`) | the Languages pages match `features.json`, the wire corpus and each runtime's report |

Editors and the CLI surface the same table: `comline targets --features` and
the language server's warnings for features a target doesn't support.
