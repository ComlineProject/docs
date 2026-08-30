# Settings

!!! note "Parsed, not yet enforced"
    `settings` blocks parse and are frozen into the version, but nothing acts on
    them yet — `forbid_indexing` and friends have no effect until field indexing
    exists in the language.

A **settings** block holds schema-wide switches.

``` py linenums="1"
/// Project-wide switches.
settings Project {
    forbid_indexing = True
    max_depth       = 8
    label           = "core"
}
```

Each entry is `key = value`, where a value is a **boolean** (`True` / `False`),
an **integer**, or a **string**. There is no expression language here.

`True` / `False` are keywords only inside a settings value — they remain valid
identifiers everywhere else (an `enum` variant named `True` still works).

## What it produces

The block freezes to a `Settings` IR unit — the name plus its `key = value`
pairs, recorded in every built version. It is not diffed, so a settings change
never bumps the package version.

The key set is not fixed yet; it is being worked out alongside the
[auto-versioning](../../design/ir-generation.md) design, which — if it lands —
removes the need for manual field indexing entirely.
