# Settings

!!! note "Planned"
    `settings` is not in the schema grammar yet. It exists as a frozen IR unit
    and the syntax below is the intended shape, not something the parser accepts
    today.

A **settings** block sets schema-wide rules — for example whether components must
be explicitly indexed.

``` py linenums="1"
settings Project {
    forbid_indexing=True
    forbid_optional_indexing=True
}
```

The values shown are the intended defaults; the exact key set is still being
worked out alongside the [auto-versioning](../../design/ir-generation.md) design
(which, if it lands, removes the need for manual field indexing entirely).
