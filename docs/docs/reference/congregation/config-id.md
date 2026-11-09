# `config.idp`

The package manifest: who the package is, what it depends on, which languages
it can be generated as, and the rules and wire defaults its schemas share. It
sits at the package root, beside `src/`. The [package author](index.md) owns
it, and it's frozen into every built version.

For a walk through it, see [Packages & dependencies](../../guides/packages/index.md).

```idp
//! The shop's API: orders, customers and payments.
congregation shop
id = "3f2a9c41d07e4b1c8a65f2e0d91b7c34"
specification_version = 1

code_generation = {
    languages = {
        rust#1.85.0 = {}
        typescript#5.0 = {}
    }
}

wire = { format = "packed@1" framing = "datagram@2" }

dependencies = {
    shared_types = {
        path = "../shared-types"
    }
}

settings = {
    annotations = {
        framing = {
            allowed = true
        }
    }
}
```

## Syntax

- **The first line** is `congregation <name>`, a Comline identifier (letters,
  digits, `_`). Everything after it is `key = value`.
- **Values** are strings (`"packed@1"`), integers, `true` / `false`, bare
  names, or dictionaries in braces. Entries in a dictionary are separated by
  new lines or spaces; there are no commas.
- **Keys don't take dots.** `.ids` settings blocks accept
  `validators.allowed = false`; here the same key is written with braces.
- **Comments** are `//`. `//!` lines at the top
  [document the package](../../guides/idl/docstrings.md#module-docs).

## Keys

| Key | Value | Details |
|---|---|---|
| `congregation` | the package's name | Renaming it is fine: `id` is what identifies the package. |
| `id` | 32 lowercase hex digits, random | The package's identity. `comline new` writes it, and `comline build` adds one to a package without it. A copy of the package must change it. Changing it is a major change. See [Compatibility facts](../versioning.md#compatibility-facts). |
| `specification_version` | an integer: `1`, the only edition so far | **Required.** The [edition](../versioning.md#editions) of the schema language the files are written in. Leaving it out, or naming an edition this Comline doesn't know, is an error with a fix that `comline fix` applies. |
| `code_generation` | `{ languages = { <language>#<version> = {} ... } }` | The languages the package can be generated as, each with the oldest toolchain its output must build on. `comline build` proves each one. See [Language versions](../../guides/codegen/generating-code.md#language-versions). |
| `wire` | `{ format = "..." framing = "..." }` | The format and framing every protocol uses unless it says otherwise. Defaults: `packed@1` and `datagram@3`. See [Wire defaults](../../guides/packages/index.md#wire-defaults). |
| `handshake` | `"comline@1"`, `"comline@2"` or `"none"`, or `{ name = "comline@2" scope = "package" }` to set [its parameters](../wire/handshakes/index.md#parameters) | What a protocol with no `@handshake` runs before its first call. Default `comline@2`, or `comline@1` in a package whose protocols aren't all on `datagram@3`. See [Giving up a guarantee](../../guides/idl/protocol.md#giving-up-a-guarantee). |
| `dependencies` | a dictionary of entries by name | Other packages this one imports, from a path or a git commit, each optionally pinned by `hash`, and what it accepts of their [`@unverified`](../../guides/idl/protocol.md#giving-up-a-guarantee) protocols (`accept_unverified`). See [Dependencies](../../guides/packages/index.md#dependencies). |
| `settings` | a dictionary, or `<dependency>::settings::<Preset>` | The package-wide authoring policy every schema starts from. See [Settings](../../guides/idl/settings.md). |
| `encodings` | a dictionary of entries by name | The formats, framings and handshakes this package defines. See [Formats and framings](../../developer/extending/encodings.md). |
| `publish_registries` | a dictionary of registries by name | Where the package can be published. Planned; see [Publishing](../../guides/packages/index.md#publishing). |

An unknown key, a value of the wrong kind, or a dependency that doesn't
resolve fails `comline check` and `comline build`, and the editor reports it
as you type.

## What's frozen, and what changes the version

`comline build` lowers the manifest to IR units and stores them with every
version, so a version carries its own declarations. A change to the manifest
counts like a schema change; the rules are in
[Manifest changes](../versioning.md#manifest-configidp-changes).

It never holds an output path: where generated code lands is the consumer's
choice, in [`comline.toml`](comline-toml.md).
