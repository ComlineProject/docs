# Links, the overview and highlighting

Status: **draft** · tracked in
[generation#144](https://github.com/ComlineProject/generation/issues/144) · a follow-up to the accepted
[Automatic documentation](index.md) · decided so far (2026-11-14): a
dependency declares where its docs are, with local pages kept beside it; the
overview shows the package's whole configuration, a private registry by name
only; built-ins link to the reference for the toolchain version that built
the package · it
**amends** the decision that docs config lives in `comline.toml` only (see
[below](#the-amended-decision))

**The question.** The renderers (`comline-doc-html`, `comline-doc-markdown`)
produce a working site. **How does it become easier to read and to move
around in?** That means four things:

- links to a dependency's docs wherever they're published;
- an overview that shows how the package is configured;
- built-in types and values that link to their reference;
- highlighting everywhere code appears, not only in signatures.

## Where things stand

- **Dependency links are manual.** A dependency's types link to its published
  docs only when the *consumer* maps it in `comline.toml`
  (`[doc] links = { billing = "https://…" }`). `std` defaults to its hosted
  docs (`STD_DOCS`). Every other dependency gets local pages
  (`deps/<package>/<module>.html`) holding only what the package reaches.
- **The model can't say more.** A `Dependency` carries its name and its
  reached modules: no version, no source (registry, git, path), no docs
  location. Registries don't record a docs location either.
- **The overview shows no configuration.** `index.html` has the title, the
  `//!` header, Modules, Dependencies and a changelog link. The model's
  `Package` is `name`, `version` and `docs`. Core's model builder
  (`core/src/doc.rs`, `model()`) has the whole project config at hand, but
  copies none of it.
- **Built-ins link nowhere.** A primitive (`Type::Primitive`) and the
  literals `true`/`false` are plain text. The page they'd link to,
  `reference/package/schema/types`, being written in the reference
  restructure, is mostly empty headings (`## bool` has no text, and there's nothing on
  floats or `()`). Its anchors don't match its names either: the guide links
  to `types#string`, which doesn't exist.
- **Highlighting follows two paths.** The HTML renderer draws a type with
  `ty_idl()` (highlighted) in signatures, constants and the module table, and
  with `ty()` (a plain `<code>`) everywhere else: field and argument tables,
  a validator's "Applies to", "Alias of". Annotations, defaults, asserts,
  messages, enum variants and settings are plain `<code>`. The tokenizer
  also treats `i8` to `i64` and `bytes` as built-ins, which the language
  doesn't have.

## 1. Links to a dependency's docs

### Where the URL comes from

In order, the first that applies:

1. **The consumer's `[doc] links`**, as today: an override, for a mirror or
   for docs the dependency doesn't declare.
2. **The dependency's own declaration** (decided): a `documentation` key in
   *its* `config.idp`. It travels with the package, so it works the same
   from a public registry, a private one, git or a path.
3. **The registry**, later: one that hosts docs itself (in the way docs.rs
   does) states where in its API. Nothing reads this until a registry
   offers it.
4. **No declaration:** local pages only, as today, so a link never leads
   nowhere.

`std` is the first case of 2: its declaration is the hosted docs, and
`STD_DOCS` goes away as a special case.

### The declaration

```idp
documentation = "https://docs.example.com/billing/{version}/{module}/#{anchor}"
```

A template with three placeholders:

| Placeholder | Filled with |
| --- | --- |
| `{version}` | the version the consumer pins |
| `{module}` | the module's path, `::` written as `/` |
| `{anchor}` | the unit's anchor, its name in lowercase; dropped with the `#` before it for a link to a module |

- **Without placeholders**, the value is a base, read as
  `{base}/{module}/#{anchor}`: today's form for `[doc] links`, so existing
  entries keep working.
- **The pinned version, not the latest.** A link from a package built against
  `billing 1.2.0` opens `billing`'s 1.2.0 docs, which still describe the type
  the package uses. A template without `{version}` links to whatever the
  dependency publishes there, and the build warns.
- **Releases only.** A consumer pinned to a dependency's pre-release or dev
  build gets local pages for it. That version's docs were never published.
- **Local pages are kept beside it** (decided). The site still renders the
  dependency's pages for what the package reaches, so the docs read in full
  offline. A type links to its local page, and each local page and the
  overview's Dependencies entry link out to the published docs at the pinned
  version (`↗ published docs`). The site works offline, and the full,
  canonical docs are one click away.
- **Never fetched.** The build doesn't check that the URL answers, so docs
  stay buildable offline. If the docs are private, the browser asks for the
  login. A `comline doc --check-links` that tries every external link could
  come later.

### The amended decision

The accepted proposal decided that "nothing about docs is frozen into a
version: whether and how docs are made is the reader's choice". The
`documentation` key keeps to the intent of that decision. **Where** published
docs live is a fact about the package, like its id, and only its author knows
it. **Whether and how** to render docs stays the reader's choice, in
`comline.toml`. The decision is amended to say so:

> Rendering is configured by the reader, in `comline.toml` only. A package
> may state where its own published docs are, in `config.idp`.

Changing `documentation` changes no wire and no API, so it's a patch.

### In the model

`Dependency` gains, additively (the model stays version 1):

| Field | What |
| --- | --- |
| `version` | the pinned version |
| `source` | where it comes from: a registry's name, a git URL, or a path |
| `documentation` | the dependency's declared template, if any |

Core fills them while compiling the dependency, which it already does. The
renderer applies the order above, with the consumer's `[doc] links` passed as
today.

## 2. The overview

### Its order

1. **The title**, version and `//!` header, as today.
2. **Package:** its id and edition (`specification_version`).
3. **Settings:** the `config.idp` `settings`, then the package's wire
   defaults (format, framing, handshake), each with where it comes from
   (`config.idp` or core's default), as a protocol's wire summary shows them.
4. **Dependencies:** each with its pinned version, its source, a link to its
   docs (by the order above), and the modules the package uses.
5. **Modules.**
6. **Code generation:** the languages and versions declared in
   `code_generation`.
7. **Registries:** the registries in `publish_registries`, each by name, and
   with its URL unless it's private ([below](#private-registries)).
8. **Changelog.**

Code generation and registries are included (decided), after what a reader
of the API needs first. They say how the package is built and published, not
what it declares.

### In the model

`Package` gains, additively, a `config` read from `config.idp`:

| Field | What |
| --- | --- |
| `id` | the package id |
| `edition` | the specification version |
| `settings` | the settings tree: key paths and values |
| `wire` | format, framing and handshake, each a value, its parameters and its source |
| `code_generation` | each language and its version |
| `registries` | each registry's name, and its URL unless it's private |

### Private registries

A private registry's URL can reveal an internal host name, so the overview
shows it by **the registry's visibility** (decided), which the author states
in `config.idp`:

```idp
publish_registries = {
    public = { url = "https://registry.comline.dev" }
    internal = { url = "https://registry.corp.example", private = true }
}
```

A private registry shows its name only, and a public one its name and URL. The
model carries no URL for a private registry at all, so no renderer can show it
by mistake. A registry is public unless marked `private`.

Like the `//!` header, it's read from the source, so documenting an older
version needs that version's `config.idp`. The proposal already notes the
same limitation [for headers](index.md#where-the-docs-come-from).

## 3. Built-ins link to the reference

**The target:** the hosted
types reference (`reference/package/schema/types`), with **one
anchor per built-in**, the name itself:

| Written | Links to |
| --- | --- |
| `bool`, `true`, `false` | `#bool` |
| `u8` … `u128`, `s8` … `s128` | `#u8` … `#s128` |
| `f32`, `f64` | `#f32`, `#f64` |
| `char` | `#char` |
| `string` | `#string` |
| `()` | `#unit` |
| a bound, `[max N]` | the [bounds](../../guides/idl/types.md#bounds) section |

- **The page comes first.** It needs real content and these anchors before
  anything links to it. The guide's broken `types#string` link gets fixed by
  the same work.
- **The toolchain's docs** (decided). A built-in links to the reference of
  the **Comline version that built the package**. The model records it, as a
  new top-level `toolchain` field (additive). The hosted base becomes a
  template, `…/{toolchain}/reference/package/schema/types/#{anchor}`. This
  needs **hosted docs versioned by toolchain release**, which the docs site
  doesn't do yet (see [What it touches](#what-it-touches)). Until it does,
  links go to the current docs, and the page says which toolchain built it.
- **Not by edition.** Editions were weighed and rejected. An edition scopes
  only the schema language, so versioning the site by edition would either
  branch the whole site for a change to one part of it, or split the language
  reference into folders per edition. Toolchain releases are the axis the
  rest of the site (CLI, generators, runtimes) versions by anyway.
- **The base is overridable** with `[doc] builtins = "…"`. That's its own key,
  because `links` is keyed by package and `builtins` could be one's name.
- **Encodings and guarantees too.** A protocol's wire summary prints
  `datagram@3`, `packed@1` and `comline@2`. Each links to its
  [reference page](../../reference/wire/official-encodings.md), and each
  guarantee row to where the guarantee is explained.
- **Quiet links.** A link inside highlighted code keeps the token's colour,
  with no underline until hovered. Otherwise every table of types turns into a
  column of links.

## 4. Highlighting everywhere code appears

**One renderer for types.** `ty()` becomes `ty_idl()` in a
`<code class="idl">`, so every type is highlighted and linked the same way,
wherever it appears. That alone fixes a validator's "Applies to", the field
and argument tables, and "Alias of".

Then each place that shows code, through the same tokenizer:

| Where | Today | Becomes |
| --- | --- | --- |
| Validator "Applies to" | plain `bool`, `Test`, `s8` | highlighted, linked |
| Field and argument **Type** columns | plain; `union(` is bare text, outside `<code>` | highlighted, linked |
| "Alias of" | plain | highlighted, linked |
| A field's default, `= true` | plain | a literal, linked when `true`/`false` |
| "(optional)" after a type | plain text | the `optional` keyword |
| Annotations, `@timeout_ms = 100` | plain | the annotation and its value |
| Validator asserts, `value > 1` | plain | an expression: names, operators, literals |
| Validator and error messages, `{value.name}` | plain text | text, with each `{…}` marked as an expression |
| An error's ordinal | plain | a literal |
| Enum variants | plain | names |
| A settings unit's keys and values | plain | a key path, and a literal or name |
| Unit headings and the module table's Item, `struct Greeting` | the kind is plain text | the kind as a keyword |
| The wire summary's encodings | plain | linked ([above](#3-built-ins-link-to-the-reference)) |

**The tokenizer** drops `i8` to `i64` and `bytes` from its built-ins. It
also gains a token for operators and one for an interpolation in a message.

**Markdown** already highlights its fenced blocks (` ```comline `), but
plain Markdown can't highlight inline code. Sites built with mkdocs and
`pymdownx.inlinehilite`, as Comline's own docs are, can, with `` `#!ids bool` ``.
The Markdown renderer gains an option for it,
`[doc.markdown] inline_highlight = true`, off by default because anywhere
else `#!ids` would show as text.

## What it touches

- **core:** the model's `Package.config` and the `Dependency` fields; the
  `documentation` key in `config.idp`; the doc model's JSON Schema.
- **cli:** `[doc] builtins` and `[doc.markdown] inline_highlight`; passing the
  pinned versions; later, `comline doc --check-links`.
- **generation:** both renderers: the overview's order and sections, the
  link order for dependencies, built-in and encoding links, one type renderer,
  and the highlighting table above; the tokenizer's fixes.
- **docs:** the types reference written out with an anchor per built-in; the
  guide's broken link; the [documenting guide](../../guides/documenting.md)
  and the [`comline.toml` reference](../../reference/package/user-configuration.md)
  for the new keys; `std` declaring its `documentation`; and **hosted docs
  versioned by toolchain release**, so that built-ins link to the reference of
  the toolchain that built a package. That's a site change of its own, worth
  its own proposal. `mike` is already configured in `mkdocs.yml`, but the
  deploy (`zensical build`, then `actions/deploy-pages` with an artifact)
  doesn't use it.
- **core:** `private` on a `publish_registries` entry.

## Decided

2026-11-14:

- **A dependency declares its docs** in its `config.idp`, as a template
  ([above](#the-declaration)), and local pages are kept beside it, for
  reading offline.
- **The overview shows the whole configuration,** code generation and
  registries included. A private registry shows by name only.
- **Built-ins link to the reference of the toolchain that built the
  package,** once the docs site is versioned by toolchain release. Not by
  edition.
- **`std` links by its own pinned version,** like any dependency: its
  `documentation` template carries `{version}`.
- **Design first:** implemented once this page is accepted.

## Open questions

- **Versioned hosted docs:** how the docs site publishes one version per
  toolchain release: `mike` on a `gh-pages` branch, or a job that builds
  release branches or tags into one artifact. It's needed once a toolchain
  release line is worth keeping docs for.
- **The amended decision** ([above](#the-amended-decision)): approving the
  new wording of the accepted proposal's config decision.
