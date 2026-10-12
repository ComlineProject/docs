# Automatic Documentation

Status: **draft** — the shape below defines what the feature *is*; none of it is
implemented, and the open questions at the end are genuinely open.

**The idea:** an optional tool that reads a built package and emits
human-readable documentation for the units a user declared in it — structs,
enums, protocols, errors, validators, constants, settings — the way `rustdoc`
or `javadoc` do for their languages. It documents **the user's schemas**, not
Comline's own sources.

## What it documents

Two sources feed it, and the first one alone is already enough to produce
something useful:

- **The declared shape**, straight out of the frozen IR: unit names, field names
  and [types](../guide/idl/types.md), enum variants, function signatures, error
  shapes, validator parameters, `@key=value` annotations. An entirely
  undocumented schema still yields a complete API listing.
- **[Docstrings](../guide/idl/docstrings.md)** — `///` on a declaration or a
  field, the `/// @name:` form for fields and arguments, and `//!` headers
  documenting a module or (in `config.idp`) the package itself. These exist
  today and, as that page notes, change nothing about a build, a version or
  generated code: they are carried for readers and tools. This is the tool.

Coverage should span every declaration form the IDL has, plus the module and
package headers that frame them — a schema's docs are the module header and its
units together, and a package's docs are its `config.idp` header and its
modules.

## Why the CAS makes this more than a doc generator

Versioning is not hand-maintained: every `comline build` freezes an immutable
version into `.comline/`, the bump is derived from the schema change itself, and
[`comline diff`](../reference/cli.md) already reports what changed between two
frozen versions. A documentation tool sitting on top of that can do what a
conventional one cannot:

- **Document any version**, not just the working tree — the frozen history is
  all still there.
- **Generate the changelog**, rather than ask someone to write it. "What changed
  in `0.3.0`" is already computable; rendering it as prose next to the affected
  units is the new part.
- **Mark a unit's history** — when a field appeared, when a function's signature
  last changed — because each unit's versions are addressable.

This is the half that distinguishes the feature from "run a generator over the
IR", and it follows from the
[CAS](../guide/ir/cas.md) and
[automatic versioning](../reference/versioning.md) already being in place.

## Optional, and the project sets the rules

It is a tool a project opts into, not a step in the pipeline. The package or the
consumer decides whether it runs at all, what it includes, and when — the same
way [`comline.toml`](../reference/congregation/comline-toml.md) already owns
generation's output location, layout and mode. Which of the two config surfaces
owns which switch is an open question below, but the principle is that nothing
here happens unless asked for.

## Open questions

- **Command or generation target?** A `comline doc` command of its own, or a
  `mode` alongside `code` and `lib`? Generation targets are per-language and
  documentation is not, so the `mode` framing fits awkwardly — but much of the
  machinery (output location, per-target config, `--watch`) is already there.
- **Output format.** Markdown for a reader to commit and publish, self-contained
  HTML, or a structured dump (JSON) that someone else renders. The three serve
  different consumers and the first two are not substitutes.
- **Config surface.** Whether the doc switches belong in the package's
  `config.idp` (the author's intent, frozen) or the consumer's `comline.toml`
  (the reader's choice, not frozen) — the same split already settled for
  [generation config](../design/consumer-generation-config.md).
- **Visibility.** Whether an annotation can keep a unit out of the output, and
  whether that is the existing `@internal` or something documentation-specific.
- **Dependencies.** Whether a unit's documentation links across to a type it
  imported with `use` from another package, and what that resolves to when the
  dependency has no published docs.
- **Templating.** Whether the output shape is fixed or themeable, which decides
  how much surface this feature has to keep stable.

## Once it ships

It lands in the product documentation, not here: a Guide page on documenting
your schemas, a `comline doc` entry in the
[CLI reference](../reference/cli.md), and whatever config keys it gains in the
[congregation reference](../reference/congregation/index.md).

The obvious first demonstration is
[the standard library](../guide/idl/use.md#the-standard-library), which already
documents itself with `//!` and `///` throughout: run the tool over `std` and
publish the result.
