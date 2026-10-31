# Formats and framings

A **format** turns values into bytes (`packed@1`, `json@1`). A **framing**
wraps a call or a reply around those bytes (`datagram@2`, `jsonrpc@1`). You
can add either one. This page covers the whole path: declare it, profile it,
prove it, map it, use it.

## 1. Declare it

A package declares the encodings it defines under `encodings` in `config.idp`:

```idp
congregation acme_lines
specification_version = 1

encodings = {
    "com.acme.lines@1" = {
        kind = "framing"
        profile = "profiles/lines.json"
        map = {
            rust = { type = "acme_lines::LinesFraming" package = "acme-lines" version = "0.1" }
            typescript = { type = "LinesFraming" package = "@acme/lines" version = "^0.1.0" }
        }
    }
}
```

| Key | Meaning |
|---|---|
| name (the entry's key) | `<namespaced name>@<n>`, such as `com.acme.lines@1`. Required. |
| `kind` | `"format"`, `"framing"` or `"handshake"`. Required. |
| `profile` | Path to the profile file, relative to the package, with no `..`. Required. |
| `map` | Optional. Per language, a suggested implementation: `type` (required), `package` and `version` (both optional). |

`comline build` checks the entry:

- the name is namespaced, has a version, and isn't declared twice;
- no other key is allowed, and `map` entries allow only `type`, `package` and
  `version`;
- the profile is readable, parses, is of the same `kind`, and is named for the
  same encoding;
- the profile states exactly the facts its kind needs, each with a value that
  fact may take.

The entry is frozen with the profile's hash, so a published version carries
what it declared.

## 2. Write the profile

A profile is a JSON file of **facts**: how the encoding behaves where it
matters to compatibility. Each fact has a value and names the vector cases that
prove it.

```json
{
  "name": "com.acme.lines@1",
  "kind": "framing",
  "facts": {
    "calls":  { "value": "by_name",    "proven_by": ["lines/request"] },
    "errors": { "value": "by_ordinal", "proven_by": ["lines/error"] }
  }
}
```

The facts are fixed per kind, and a profile must state all of them:

| Kind | Fact | Values |
|---|---|---|
| format | `struct_fields` | `by_position`, `by_name` |
| format | `unknown_field` | `rejected`, `ignored` |
| format | `missing_optional` | `rejected`, `absent` |
| format | `enum_variants` | `by_name`, `by_index` |
| format | `unknown_variant` | `rejected`, `tolerated` |
| format | `integer_width` | `by_value`, `exact` |
| framing | `calls` | `by_index`, `by_name`, `by_id` |
| framing | `errors` | `by_ordinal`, `by_name` |
| handshake | none | a handshake profile is `"facts": {}` |

The facts are what the version comparison reads, so a profile is fixed for its
version: changing a fact means a new `@n`. The comparison rules themselves are
still a [proposal](../../proposals/schema-compatibility.md#encoding-profiles).
For the official profiles, see the
[runtime's `profiles/`](https://github.com/ComlineProject/runtime/tree/main/runtime/conformance/profiles).

## 3. Write vectors, and prove an implementation

**Vectors** are byte-exact cases. They sit beside the profile: the profile's
path with `.json` replaced by `.vectors.json`, so `profiles/lines.json` has
`profiles/lines.vectors.json`.

```json
{
  "feature": "lines",
  "cases": [
    {
      "id": "lines/error",
      "op": "response",
      "input": { "framing": "com.acme.lines@1", "kind": "err",
                 "request_id": "7", "id": 2, "body": "6e6f" },
      "bytes": "455252203720322036653666"
    },
    {
      "id": "lines/reject-unknown-kind",
      "op": "response",
      "input": { "framing": "com.acme.lines@1" },
      "bytes": "4d415942452039",
      "expect": "reject"
    }
  ]
}
```

- A framing uses the `request` and `response` ops. A format uses `encode` and
  `decode`.
- `bytes` is lowercase hex. 64-bit integers are decimal strings.
- `"expect": "reject"` says the bytes must be refused.
- Every `proven_by` entry in the profile names a case in this file.

The case format is a public, versioned spec: see the
[conformance reference](../../reference/conformance.md) for the ops, the value
encoding and the rules a case is judged by.

To run it, write a small program that speaks the **ops protocol**: one JSON
request per line on stdin, one reply line each on stdout, exit 0 when stdin
ends. Its `version` reply lists the encodings it implements. Then:

```
comline conformance --impl ./target/release/acme-lines-conformance
```

The report gives, per encoding, how many cases pass, whether each profile fact
is **proven** (every case it names passes and shows its value), and a byte diff
for each failed encode. A failed or unimplemented case, or an unproven fact,
exits with `1`. The flags, limits and report are in the
[CLI reference](../../reference/cli.md#commands).

- `comline conformance` runs every encoding the package declares. An encoding
  with no vectors file is an error, so name the ones you mean with
  `--encoding`.
- Official encodings are proven in the runtime's corpus. Run them with
  `--corpus <runtime>/runtime/conformance`.

## 4. Use it in a schema

Once a package declares an encoding, it, or a package that depends on it, can
name it:

```idp
wire = { format = "com.acme.codec@1" framing = "com.acme.lines@1" }
```

```ids
@framing = "com.acme.lines@1"
protocol Billing { /* ... */ }
```

A namespaced name that nothing declares is a build error: *"framing
`com.acme.lines@1` isn't declared: declare it under `encodings` in this
package's config.idp, or depend on a package that does"*. It is never quietly
replaced by a default.

Two limits apply:

- A framing written as `{ name = "com.acme.lines@1" }` allows no other key.
  `method_names` is for JSON-RPC only.
- A format serializes the data the generated code already produces. A format
  that needs more from the schema, such as field tags, isn't a plug-in: it
  needs a language feature.

## 5. Map it to a type

Generated code has to name a type that implements the encoding in each target
language. The mapping comes from two places, and the first one that answers
wins:

1. **The consumer's override**, in `comline.toml`.
2. **The declaring package's `map`** for that language.

If neither answers for an encoding the package uses, `comline generate` fails
with one sentence per encoding:

```text
encoding `com.acme.lines@1` has no rust mapping: map it in comline.toml, under `[generate]`
or the target, as `encodings = { "com.acme.lines@1" = "<type>" }` ...
```

The override is a table in `comline.toml`, on `[generate]` for every target or
on one `[[generate.target]]`:

```toml
[generate]
encodings = { "com.acme.lines@1" = "acme_lines::LinesFraming" }

[[generate.target]]
language  = "rust"
encodings = { "com.acme.lines@1" = { type = "acme_lines::LinesFraming", package = "acme-lines", version = "0.1" } }
```

A value is the type alone, or a table of `type`, `package` and `version`. A
target's entry beats `[generate]`'s, name by name. An official encoding may be
written in any spelling (`jsonrpc@1` and `json-rpc` are one entry).

What the generated code does with the type:

- **Rust:** a framing or handshake type is written as a bare path, such as
  `acme_lines::LinesFraming`, so it needs to be a unit struct (or constant). A
  format type is built with `Type::default()`.
- **TypeScript:** the type is a class, built with `new LinesFraming()`, and is
  imported from `package` when one is given. A mapping with no `package`
  assumes the class is already in scope.
- **`lib` mode** adds `package` to the generated `Cargo.toml` or
  `package.json`, at `version` (`*` if there is none), when
  the generated code names a type from it. The official runtime package is
  already a dependency. **`code` mode** has no manifest to edit, so adding the
  dependency is yours to do.

Your implementation has to exist as a trait implementation in the runtime:
`Framing` and `WireFormat` in Rust, `Framing` and `Codec` in TypeScript. The
format traits aren't sealed, so a third-party one is possible.

## Becoming official

A third-party encoding becomes official by contributing its profile, vectors
and implementations to the official packages. It keeps its namespaced name,
because renaming it would change the handshake and break existing peers.
