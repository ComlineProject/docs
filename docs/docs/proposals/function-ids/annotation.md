# Proposal A — an `@id` annotation

Status: **under discussion** · See the [section overview](index.md) for the
question both answer

**The idea:** the id is an annotation on the function, an integer like
`@timeout_ms`'s value. The same annotation on a protocol gives its family id.

## Shape

```ids
@provider = Server
@id = 2
protocol LoginServerbound {
    @id = 0x00
    function hello(protocol_version: u32, name: string);

    @id = 0x02
    function acknowledged();
}
```

## The case for it

- **It works with today's machinery.** An integer annotation is parsed, frozen
  and type-checked like every other known annotation. Only hex literals are
  new, and they're needed either way.
- **One form for functions and families.** `@id` on a protocol is the family
  id. Nothing else to learn.
- **It reads like the other per-function settings** (`@timeout_ms`,
  `@idempotent`), so the editor's completion, hover and value checks apply
  unchanged.
- **Settings can govern it** like any annotation, for example requiring ids in
  a package, through `annotations.id`.

## The case against

- **It doesn't read like a packet table.** In a long protocol the ids sit on
  their own lines above each function, not in a column, and that column is how
  packet tables are usually read and reviewed.
- **It looks like metadata, but it's identity.** Under a packet framing the id
  *is* the packet. An annotation makes it look as optional and secondary as a
  timeout.
- **Annotations are an open namespace,** so a typo (`@ids = 2`) parses. Known
  annotations are checked, and a packet framing requires every id, so the typo
  surfaces, but as "missing id" rather than "unknown annotation".

## When this would be the right call

If consistency with the rest of the language matters most, and ids are mostly
written once and read through tooling.
