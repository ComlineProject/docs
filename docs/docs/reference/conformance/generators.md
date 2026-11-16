# Generator conformance

How each code generator's output is pinned, and how its feature support is
proven. Generation holds the fixture corpus and a generator-agnostic harness;
each generator runs the harness against its own goldens and publishes its own
report. The source of truth for the corpus and the harness is the generation
repository's
[`conformance/README.md`](https://github.com/ComlineProject/generation/blob/master/conformance/README.md);
each generator's side is its `codegen/tests/conformance.rs`
([comline-rust](https://github.com/ComlineProject/comline-rust),
[comline-typescript](https://github.com/ComlineProject/comline-typescript)).

## Flow

1. **Fixtures.** Each fixture in generation's `conformance/src/lib.rs` is one
   schema as hand-built IR (`Vec<FrozenUnit>`), not parsed source. The corpus
   pins IR shape, not parser behaviour. A generator pins a revision of
   generation, so a change to a fixture reaches it as drift in its own suite,
   and its pull request carries the new goldens.
2. **Goldens.** A generator's test describes it to the harness (its language,
   entry point, `SUPPORT` table and version boundaries), which runs it over
   every fixture and diffs the output against the goldens the generator holds
   under `codegen/tests/golden/<fixture>/<lang>[@<boundary>]/`. A golden is a snapshot of
   what the generator does now, not what it should do: a change in output
   shows up in that pull request's diff and is re-blessed deliberately.
3. **Support claims.** Each generator states what it implements in its
   `SUPPORT` table (`comline_codegen::features`). The harness's
   `support_is_proven` checks every claim against the fixtures.
4. **Outputs.** The proven table is written to `FEATURES.md` and
   `features.json` at the generator's repository root, by the same run that
   blesses its goldens. Each file has the generator's own entry in
   `generators` and the same `features` list as the other generator's.
5. **Consumers.** The [Languages](../languages/index.md) pages and the
   [Observatory](reports.md)'s `codegen` matrix read each generator's
   `features.json` from its default branch and join them into one table.

```sh
# in a generator's repository, here comline-rust
cargo test -p comline-codegen-rust --test conformance                    # check
CONFORMANCE_BLESS=1 cargo test -p comline-codegen-rust --test conformance # regenerate goldens and FEATURES
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
| each generator (comline-rust, comline-typescript) | every pull request and push (`cargo test`) | goldens match; every claim is proven; its `FEATURES.md` and `features.json` are current |
| generation | every pull request and push (`cargo test`) | the corpus and the harness build and pass the tests that need no generator |
| docs | weekly (`language-support-drift.yml`) | the Languages pages match both generators' `features.json`, the wire corpus and each runtime's report |

Editors and the CLI surface the same table: `comline targets --features` and
the language server's warnings for features a target doesn't support.
