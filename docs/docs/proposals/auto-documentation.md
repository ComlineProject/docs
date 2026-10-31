# Automatic Documentation

Status: **accepted** · decided 2026-11-01 · tracked in
[core#145](https://github.com/ComlineProject/core/issues/145) · the doc model is
being built in core
([core#151](https://github.com/ComlineProject/core/pull/151)); the command,
config and renderers are not built yet

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
frozen versions. A documentation tool built on top of that can do what a
conventional one cannot:

- **Document any version**, not just the working tree — the frozen history is
  all still there.
- **Generate the changelog**, rather than ask someone to write it. "What changed
  in `0.3.0`" is already computable; rendering it as prose next to the affected
  units is the new part.
- **Mark a unit's history** — when a field appeared, when a function's signature
  last changed — because each unit's versions are addressable. This comes after
  the first release.

This is the half that distinguishes the feature from "run a generator over the
IR", and it follows from the
[CAS](../guide/ir/cas.md) and
[automatic versioning](../reference/versioning.md) already being in place.

## Optional, and the project sets the rules

It is a tool a project opts into, not a step in the pipeline. Nothing here
happens unless asked for. The consumer's
[`comline.toml`](../reference/congregation/comline-toml.md) owns the switches,
the same way it already owns generation's output location, layout and mode.

## Decisions

These were open questions until 2026-11-01. The rationale is in
[core#145](https://github.com/ComlineProject/core/issues/145).

- **Command or generation target: both.** A `comline doc` command for ad-hoc
  use, plus an optional doc section in `comline.toml` for regular builds.
  Documentation isn't a `mode` alongside `code` and `lib`: generation targets
  are per language, and documentation is not.
- **Config surface: `comline.toml` only.** Nothing about docs is frozen into a
  version. Whether and how docs are made is the reader's choice, as with
  [generation config](../design/consumer-generation-config.md). The author's
  part is the docstrings themselves.
- **Output: a JSON model, rendered by separate programs.**
    - A versioned JSON **doc model** is the one contract, with its JSON Schema
      on this site. It holds the package and module headers, every unit with its
      docstrings (the `/// @name:` lines split out per field and argument), each
      type that names another unit linked to where that unit is declared, each
      protocol's wire summary from `comline inspect`, and the changelog.
    - **Renderers** are external programs on the same stdio protocol as
      [generators](../reference/generator-protocol.md), native or `.wasm`.
    - The first official renderer writes **Markdown with navigation** for
      mkdocs/zensical sites. Rendering [`std`](../guide/idl/use.md#the-standard-library)
      onto this site proves it.
- **History: any version, and a changelog.** Any frozen version can be
  documented. The changelog comes from the same analysis as `comline diff`.
  Per-unit "since" markers (when a field appeared, when a signature last
  changed) come later.
- **Visibility: everything is documented.** There is no way to hide a unit and
  no annotation for it, `@internal` included.
- **Dependencies: linked when they say where their docs are.** A unit's docs
  link to a type it imported from another package when `comline.toml` maps that
  dependency to the URL of its docs. Without a mapping, the type shows as plain
  text.
- **Templating: the renderer's business.** Theming belongs to each renderer.
  Core keeps no template surface, and the model is the only thing it keeps
  stable.

## Where the docs come from

- A unit's `///` docstring is part of the frozen IR, so a frozen version
  already has its unit docs.
- The `//!` module and package headers are not frozen. They're read from the
  source: a module's from its `.ids` file, and the package's from `config.idp`.
  Documenting an older version's headers needs the source of that version, or
  needs the headers added to what gets frozen. Neither is decided yet.

## Once it ships

It lands in the product documentation, not here: a Guide page on documenting
your schemas, a `comline doc` entry in the
[CLI reference](../reference/cli.md), its `comline.toml` keys in the
[congregation reference](../reference/congregation/index.md), and the doc
model's JSON Schema.

The obvious first demonstration is
[the standard library](../guide/idl/use.md#the-standard-library), which already
documents itself with `//!` and `///` throughout: run the tool over `std` and
publish the result.
