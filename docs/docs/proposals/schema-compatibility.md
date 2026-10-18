# Schema compatibility

Status: **under discussion** · tracked in
[core#119](https://github.com/ComlineProject/core/issues/119) · nothing here is
implemented

**The question:** which schema changes are breaking, and so which version bump
a build takes. A bump is only worth something if it tells a reader whether an
old peer can still talk to a new one, and whether code written against the old
version still finds what it uses. Today it says neither reliably.

## Where things stand

[Versioning rules](../reference/versioning.md) describes the bump a build takes.
The comparison behind it (`core/src/schema/ir/diff.rs`) looks at a fraction of
the schema:

- **Not compared at all:**
  - annotations, including `@framing` and `@validators`;
  - type aliases and validator declarations;
  - constants, beyond their docstring;
  - an error's fields, message and ordinal;
  - argument names;
  - a field's `optional` flag.
- **Removing an optional field reports nothing.**
- **Types are compared as written,** so changing `string` to `Handle`
  (`type Handle = string`) is reported as breaking
  ([core#110](https://github.com/ComlineProject/core/issues/110)).
- **Schema files are paired by their position** in the glob, not by namespace.

[core#118](https://github.com/ComlineProject/core/issues/118) lists these.

The rules it does apply also disagree with the wire in places, because what a
change breaks depends on how it travels:

- **MessagePack encodes a struct as a positional array.** Generated Rust has no
  `#[serde(default)]`, so adding even an optional field at the end breaks the
  other side, and so does reordering fields. JSON keys fields by name and
  tolerates both. Today adding an optional field is minor, whichever format the
  package uses.
- **`datagram` framing addresses a call by its function's declaration index.**
  Inserting a function before others re-addresses them. `jsonrpc` addresses
  calls by name.
- **An error travels as its ordinal.** Local errors are numbered in declaration
  order, so inserting one renumbers the rest.
- **Enum variants travel by name,** so reordering them changes nothing.

Finally, the handshake compares a hash of the **whole** frozen schema, spans and
docstrings included. Any edit, even a reformat, makes old and new peers refuse
each other, so no bump can be relied on at runtime yet
([runtime#15](https://github.com/ComlineProject/runtime/issues/15)).

## What "breaking" protects

> A change is **breaking** if an old peer and a new peer can no longer exchange
> messages, or if a name that consumers refer to disappears.

The names are those of a type, member, alias, constant, validator, or a
generated error variant. Generated code doesn't have to stay
source-compatible in every respect. Adding a field to a Rust struct breaks a
consumer's struct literal, and counting that would make almost every change
major.

- **Minor:** an addition that an old peer and old consumer code don't depend
  on.
- **Patch:** a change that alters nothing on the wire and removes no name, such
  as documentation, advisory annotations or a respelled type.

## Versioned formats and framings

The rules depend on the encoding, so the encoding must be named exactly, and the
package must say which ones it speaks.

- **Every format and framing gets a version:** `json@1`, `msgpack@1`,
  `datagram@1`, `jsonrpc@1`. A third-party one is namespaced
  (`com.acme.cbor@1`). A later encoding, such as a name-keyed `msgpack@2`
  ([runtime#16](https://github.com/ComlineProject/runtime/issues/16)), gets a
  new version instead of silently changing what `"msgpack"` means.
- **A name must be specific.** `@framing = "jsonrpc"` becomes a build error
  that suggests `"jsonrpc@1"`, with an editor quick fix, and there is no
  deprecation period. The handshake carries the versioned names
  ([runtime#14](https://github.com/ComlineProject/runtime/issues/14)).
- **The package declares what it speaks** in `config.idp`
  ([core#117](https://github.com/ComlineProject/core/issues/117)):

  ```
  wire_formats = ["json@1", "msgpack@1"]
  framings = ["datagram@1", "jsonrpc@1"]
  ```

  The key names are open. Today the format is a call-site choice
  (`MailClient::connect(transport, MsgPack)`), and a protocol's framing falls
  back to the consumer's `default_framing` in `comline.toml`. Neither is part of
  the frozen package, so the comparison can't see them.
- **The comparison applies the strictest rules among the declared
  encodings.** With none declared, the package is taken to speak every known
  one.
- **Generated code offers only the declared formats**
  ([generation#67](https://github.com/ComlineProject/generation/issues/67)).
  In Rust, this could be a sealed trait implemented only for them.

## Encoding profiles

A format doesn't declare which bumps its changes take. It declares **facts about
its encoding**, and the comparison turns those facts into bumps with one set of
rules.

The facts are what can be tested. "`json@1` ignores an unknown field" is true or
false, and a conformance vector shows which; "adding an optional field is minor
under `json@1`" has no such test. If every format carried its own table of
bumps, each could quietly decide policy differently, and the rules would be
copied once per format.

### What a profile states

A format and a framing are chosen separately, so each has its own profile:

```jsonc
// msgpack@1 (format)
{
  "struct_fields": "by_position",   // or "by_name"
  "unknown_field": "rejected",      // or "ignored"
  "missing_optional": "rejected",   // or "absent"
  "enum_variants": "by_name",       // or "by_index"
  "unknown_variant": "rejected",    // or "tolerated"
  "integer_width": "by_value"       // a wider integer decodes if its value fits
}

// datagram@1 (framing)
{
  "calls": "by_index",              // jsonrpc@1: "by_name"
  "errors": "by_ordinal",
  "one_way": "no_reply_frame"
}
```

The property set is small and fixed, so the comparison knows every value it can
meet. A new property is a change to the comparison too, not something a format
can add on its own.

### How a rule reads them

Each rule that depends on the encoding is written once, against properties:

- **Add an optional field:** major if `struct_fields` is `by_position`,
  `unknown_field` is `rejected` or `missing_optional` is `rejected`; minor
  otherwise.
- **Insert a function before others:** major if `calls` is `by_index`; none
  otherwise.
- **Reorder enum variants:** major if `enum_variants` is `by_index`; none
  otherwise.

Over the formats and framings a package declares, the strictest result wins. The
reported reason names the property that decided it: "major under `msgpack@1`:
fields are positional". That reason tells the author what to change, or which
encoding to drop.

Some outcomes depend on values, not shape. A wider integer only fails on a value
the old reader can't hold. These stay major, with the reason saying so, rather
than introducing a "maybe" level.

### Where profiles live

1. **The runtime's conformance corpus is the source.** It holds one profile per
   versioned name beside `features.json`, for example
   `runtime/conformance/profiles/msgpack@1.json`. Every property is backed by a
   vector:
   - "`msgpack@1` rejects an unknown field" is a vector with `"expect": "reject"`;
   - "`json@1` ignores one" is a vector that decodes.

   A profile then can't claim something the runtime doesn't do, the same
   guarantee the support tables already have.
2. **Core keeps a pinned copy for the encodings it knows,** because core can't
   depend on the runtime. It's drift-checked against the corpus, the way
   comline-typescript vendors the vectors.
3. **A profile is fixed for its version.** If a property changes, that is a new
   version: `msgpack@2` is `msgpack@1` with `struct_fields: by_name` and
   `missing_optional: absent`. That defines what the `@N` in a name means.
4. **An encoding core doesn't know** is compared under the strictest profile,
   with a warning saying so.

The `config.idp` declaration stays names only; the profiles come from the
corpus.

## The rules

Types are compared **after resolving aliases**, each version through its own.
The bump a build takes is still the largest of its changes.

Where a row below names a format or framing, that's the rule applied to today's
profiles; the rule itself is written against the property, as above.

### Fields (structs, and error bodies)

| Change | Bump | Why |
|---|---|---|
| add an optional field | minor under `json@1`; **major under `msgpack@1`** | JSON readers ignore unknown fields and read a missing one as absent; `msgpack@1` is positional |
| add a required field | major | an old writer never sends it |
| remove a field | major | a name disappears (and a required one stops arriving) |
| required → optional | major | a new writer may send `null`, which an old reader rejects |
| optional → required | major | an old writer may send `null` |
| reorder fields | none under `json@1`; major under `msgpack@1` | |
| change the type | major | including widening: an old reader fails on a value outside its range, and in TypeScript `u32` → `u64` changes `number` to `bigint` |
| swap the type for an equivalent alias, either way | patch | same bytes, same generated type; reported as "same type, respelled" |
| change the default | patch | defaults never reach the wire |

### Enums

| Change | Bump | Why |
|---|---|---|
| add a variant | minor | conventional, with a caveat: an old reader can't decode the new variant, so a peer must not send it to one that predates it ([runtime#17](https://github.com/ComlineProject/runtime/issues/17) asks whether readers should tolerate unknown variants) |
| remove or rename a variant | major | |
| reorder variants | none | variants travel by name |

### Protocols and functions

| Change | Bump | Why |
|---|---|---|
| add a function at the end | minor | |
| insert a function before others, or reorder | major under `datagram@1`; none under `jsonrpc@1` | `datagram@1` calls by index |
| remove a function | major | |
| rename, add, remove or reorder an argument | major | JSON keys arguments by name; MessagePack and Rust's positional signature by order |
| change the return type | major | |
| switch between one-way and request/response | major | one side waits for a reply the other never sends, or gets one it doesn't expect |
| add an error to `!` | minor | an old client receives it as `Remote` |
| remove an error from `!` | major | a generated error variant disappears |
| `@framing` changes | major | compared in canonical, versioned form |

### Errors

| Change | Bump | Why |
|---|---|---|
| append a new error | minor | |
| insert, remove or reorder local errors, so that an ordinal changes | major | the ordinal is what travels |
| change the fields | as for fields | the body is encoded like a struct |
| change the message | patch | rendered client-side, never sent |

### Constants, aliases and validators

| Change | Bump | Why |
|---|---|---|
| add a constant, alias or validator | minor | |
| remove one | major | a name disappears |
| change a constant's type | major | |
| change a constant's value | minor | open: see below |
| change an alias's target | major, at every use | |
| a field's **effective validators** change, other than by removal | major | what's accepted narrows; with `validate_on_decode`, old data is rejected |
| validators only removed from a field | minor | what's accepted widens |

A field's effective validators are those on its alias chain, innermost first,
then its own, with every argument resolved against its default. If a validator
in that set changes its body or its targets, the set has changed too. Telling a
genuine tightening from a loosening in general would mean comparing conditions.
So any change other than pure removal counts as narrowing.

### Annotations and documentation

| Change | Bump |
|---|---|
| `@deprecated` added | minor |
| `@deprecated` removed, or its message changed | patch |
| `@timeout_ms`, `@idempotent`, or an annotation Comline doesn't know | patch |
| `@settings`, or a `settings` block | none: these only govern the build |
| any docstring, on a declaration or a member | patch |

### The package

| Change | Bump |
|---|---|
| a declared format or framing removed | major |
| a declared format or framing added | minor |

Schema files are matched by namespace, so adding, renaming or reordering files
doesn't pair the wrong ones.

## Open questions

- **Third-party profiles.** An encoding core doesn't know gets the strictest
  profile. [Extending the call system](extensibility.md#how-core-learns-about-one)
  proposes that the package defining it declares its profile, trusted like its
  schemas. Is that trust enough?

- **A constant's value.** Constants never travel, but they often encode limits
  that both peers rely on, such as a maximum length. Should a value change be
  major?
- **Narrowed validation as its own category.** It's major above. Should it be
  reported separately, so a reader can tell it from a shape change?
- **Unknown enum variants.** If readers tolerated them
  ([runtime#17](https://github.com/ComlineProject/runtime/issues/17)), adding a
  variant would be safely minor instead of minor with a caveat.
- **Framing without `@framing`.** Should such a protocol take the package's
  single declared framing, or the consumer's `default_framing` among the
  declared ones?
- **An escape hatch.** Should an author be able to accept a breaking change
  without a major bump, and should the build be able to fail on one?
  ([cli#80](https://github.com/ComlineProject/cli/issues/80))
- **The handshake.** Until it checks compatibility instead of identity
  ([runtime#15](https://github.com/ComlineProject/runtime/issues/15)), the bump
  is advisory. Should that come first?

## What it touches

- **core:**
  - the comparison, with rules written against profile properties;
  - a pinned, drift-checked copy of the known profiles;
  - the `config.idp` declaration;
  - versioned `@framing` values and their error;
  - pairing schemas by namespace.
- **runtime:** versioned names in the handshake, a profile per versioned name in
  the conformance corpus with a vector behind every property, and the
  re-blessed vectors. comline-typescript's vendored copy follows.
- **generation**, **comline-rust** and **comline-typescript:** the declared
  formats reach generated code.
- **cli:** reporting the full set of changes and the bump in `build` and `diff`
  ([cli#80](https://github.com/ComlineProject/cli/issues/80)).
- **language server:** the quick fix for a bare format or framing name.
- **docs:** [Versioning rules](../reference/versioning.md), rewritten once the
  rules are agreed.
