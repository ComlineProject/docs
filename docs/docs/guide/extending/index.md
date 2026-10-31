# Extending Comline

Comline has five places where you can bring your own code. This section is a
guide to each. What a page describes is built and shipped; what isn't is
listed under [What isn't built](#what-isnt-built).

| You want to | What it is | Declared in the schema? | Guide |
|---|---|---|---|
| Encode values another way | a **format** | yes, by name, in `config.idp` | [Formats and framings](encodings.md) |
| Frame calls another way | a **framing** | yes, by name, in `config.idp` | [Formats and framings](encodings.md) |
| Open a connection with your own hello | a **handshake** | yes, by name, in `config.idp` | [Handshakes](handshakes.md) |
| Generate code for another language | a **generator** | no, it is a program | [Generators](generators.md) |
| Carry frames over another medium | a **transport** | no, it is runtime code | [Transports](transports.md) |
| Log, authorise or meter calls | a **dispatcher** wrapper | no, it is runtime code | [Dispatchers](dispatchers.md) |

## The rules behind it

- **Official and third-party extensions use the same mechanism.** `packed@1`,
  `datagram@2` and `comline@1` are declared the way `com.acme.lines@1` would
  be: by an `encodings` entry in a `config.idp`. The official ones come from a
  package built into the toolchain, as `std` does. See the
  [design](../../proposals/extensibility.md).
- **Only what changes the bytes on the wire is declared.** Formats, framings
  and handshakes are named, versioned and profiled, because two peers have to
  agree on them. Transports and dispatchers don't change the bytes, so they
  are plain code in your program.
- **Names are namespaced.** A third-party encoding is named like
  `com.acme.lines@1`: lowercase segments joined by dots, at least two, then
  `@` and a whole number. A bare name such as `json@1` is reserved for the
  official package, and `comline build` rejects it anywhere else.
- **Proof is optional but visible.** An encoding can ship test vectors that
  prove an implementation, run with [`comline conformance`](../../reference/cli.md#commands).
  Nothing forces you to write them, but a format or framing without them, and
  a handshake whose profile doesn't state what it establishes, give up a
  guarantee that the schema must mark with `@unverified`. See
  [Giving up a guarantee](../idl/protocol.md#giving-up-a-guarantee).

## How the pieces connect

For an encoding, the same name travels through four steps:

1. **A package declares it** under `encodings` in `config.idp`, with a kind
   and a profile, and optionally a suggested type per language.
2. **A schema uses it** by name: in `wire`, `handshake`, `@framing` or
   `@handshake`.
3. **A consumer maps it** to a type in each target language, in
   `comline.toml`, when the package didn't already suggest one.
4. **Generated code uses that type** where it would use `Datagram2Framing` or
   `ComlineHandshake`. An encoding that is used but has no mapping for a
   target is a generation error. There is no fallback.

## Registry names

A package can publish its mapping with a package name and version, so
generated `lib` output adds the dependency itself. Names in a hosted registry,
and a registry that resolves them, are deferred to the registry itself,
recorded on [core#8](https://github.com/ComlineProject/core/issues/8). Today a
generator or a dependency is a local path or a git dependency you name.

## What isn't built

- **Compatibility comparison of third-party profiles.** A profile is frozen
  into the package (its hash is stored), but the [schema compatibility
  rules](../../proposals/schema-compatibility.md) that read its facts are
  still a proposal.
- **Playground UI for external generators.** The playground can run a WASI
  generator in a worker, with the CLI's limits, but nothing in its interface
  reaches that yet. See [Generators](generators.md#the-playground).
- **A registry** for encodings and generators, as above.
