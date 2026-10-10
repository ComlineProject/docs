# Settings

**Settings** are package/schema-wide *authoring policy* — "only this
annotation here," "no validator overrides there" — enforced as a hard build
error, not a style suggestion. They come in three layered forms, and in one
cross-package form that adopts another package's policy wholesale.

## Package-wide default — `.idp`

Every package has a `settings` field in its manifest (`config.idp`). A
package that writes none still gets [Comline's built-in
default](#the-built-in-default) — this is the base every schema layers on
top of.

```idp linenums="1"
congregation acme
specification_version = 1

settings = {
    annotations = {
        framing = {
            allowed = true
        }
    }
}
```

`.idp` has no dotted-key sugar (that's `.ids`-only, see below) — nested keys
need real braces, as above.

## Schema-wide — unnamed `.ids` block

A schema file can have one **unnamed** `settings {}` block, applying
implicitly to just that file, layered on top of the package default:

```ids linenums="1"
settings {
    validators.allowed = false
}
```

`.ids` *does* support dotted-key sugar — `validators.allowed = false` desugars
to the same nested shape `.idp`'s `validators = { allowed = false }` would
produce.

## Named presets — `@settings`

A schema file can also have any number of **named** `settings Name {}`
blocks. These are not auto-applied — they are reusable presets, opted into
per-declaration with `@settings = Name`, the same annotation mechanism that
attaches `@validators` or `@framing`:

```ids linenums="1"
settings Strict {
    validators.mode = replace
    validators.allowed = true
}

@settings = Strict
struct Payment {
    amount: u64
}
```

## How the layers compose

For any one declaration, three layers merge in order — package default →
schema's own unnamed block → named preset (if `@settings` is used) — each one
overriding what came before it, recursively, key by key.

**Merge is the default**; a subtree can opt out with the reserved bare
keyword `mode = replace`, which drops the layer below entirely instead of
merging into it:

```ids linenums="1"
settings {
    validators = {
        mode = replace
        allowed = true
    }
}
```

## Keys

A settings key always ends in `.allowed` and takes a boolean (`True` /
`False` — keywords only inside a settings value; an `enum` variant literally
named `True` still works everywhere else):

```
[<decl-path>.]<category>[.<name>].allowed = bool
```

- `<decl-path>` mirrors real schema nesting (`struct.field`, `protocol`,
  `error.field`) and is omittable for a global toggle.
- `<category>` is `annotations` or `validators`.
- `<name>` optionally narrows to one member of that category — an
  annotation's name, or a validator's name.

A more specific key always wins over a less specific one. For an annotation,
the lookup order is decl-scoped then global:
`<decl-path>.annotations.<name>.allowed` → `annotations.<name>.allowed`. For a
validator reference, the specific name wins over the coarse "any validator"
form at each scope:
`<decl-path>.validators.<name>.allowed` → `<decl-path>.validators.allowed` →
`validators.<name>.allowed` → `validators.allowed`.

Examples:

| Key | Meaning |
|---|---|
| `validators.allowed` | validators usable anywhere |
| `struct.field.validators.allowed` | validators usable on struct fields specifically |
| `protocol.annotations.framing.allowed` | `@framing` usable on protocols |
| `validators.StringBounds.allowed` | kill one validator kind everywhere |

No key at any level means **allowed**, with one named exception — see below.

## Enforcement

A forbidden annotation or validator reference is always a **hard build
error** naming the annotation/validator and the exact key that forbade it —
there is no `severity = "warn"` escape hatch. This also surfaces live in the
language server, not just at `comline check`/`build` time.

```
error: annotation '@framing' is forbidden here by 'annotations.framing.allowed = false'
  ...
  Help: remove '@framing', or set 'annotations.framing.allowed = true' to allow it
```

## The built-in default

Comline ships exactly one built-in default policy: **`@framing` is forbidden
until some level explicitly allows it.** Wire framing (`jsonrpc` vs.
`datagram`) is a wire-compatibility decision an organization should make
deliberately once, not something any individual protocol can silently flip —
so a package that writes no `settings` at all still gets
`annotations.framing.allowed = false`. Every other annotation and validator
stays allowed by default. Write `settings = { annotations = { framing = {
allowed = true } } }` (or a decl-path-scoped form) to permit it.

## Cross-package sharing

A package's `.idp` can adopt another package's named preset directly as its
own package-wide default, instead of copy-pasting the block:

```idp linenums="1"
settings = shared_types::settings::Strict
```

This resolves `Strict` against the `shared_types` dependency's own schemas
(it must be declared in this package's `dependencies`), and adopts that
block's content wholesale — no further merging against `shared_types`' own
package default. If more than one schema in `shared_types` defines a
`settings Strict {}` block, that's an ambiguity error naming both. The
reference is not transitive: `Strict` itself can't be another cross-package
reference — a referenced preset must be concrete.

## What it produces

Every form freezes to a `Settings` IR unit holding the resolved `key = value`
pairs. It is not diffed, so a settings change alone never bumps the package
version.
