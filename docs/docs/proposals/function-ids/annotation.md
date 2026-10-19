# Proposal A — an `@id` annotation

Status: **accepted** · with the points settled [below](#as-accepted) ·
tracked in [core#127](https://github.com/ComlineProject/core/issues/127) · See
the [section overview](index.md) for the question both answer

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

## As accepted

- **The radix isn't a setting.** `0x2A` and `42` are the same id, so a setting
  would make a style choice part of the language. The formatter normalises
  ids to one radix, and a style lint (say `style::id-radix`) can be raised to
  an error through the existing `diagnostics.<code>.level`.
- **Ids can be assigned on build.** A settings key in the existing path shape,
  e.g. `protocol.function.ids.assign`:

  | Value | Effect |
  |---|---|
  | `write` | `comline build` gives every function without `@id` the next free id, **writes `@id` into the source**, and prints what it wrote |
  | `require` | a function without `@id` is a build error; packet framings imply this |
  | `off` | ids are optional; datagram falls back to position, as today |

  **The default is derived from the package's framings**, since ids matter only
  when the wire addresses calls by number:

  | A package's framings address calls | Default | Why |
  |---|---|---|
  | by id (`comline.packet@1`) | `require`, and it can't be lowered | the id *is* the packet |
  | by name only (`jsonrpc@1`) | `off` | ids would be unused |
  | by position (`datagram@1`, core's default) | `off` during `0.x`, then `write` from 1.0 | see below |

  - **For datagram, ids are tied to stabilisation.** During `0.x`, reordering is
    breaking but only a minor bump, and nothing edits sources unasked. When
    `comline release 1.0`
    ([cli#82](https://github.com/ComlineProject/cli/issues/82)) stabilises the
    package, it assigns ids to every function, writes them into the source,
    and switches the setting to `write`. From then on new functions get ids on
    build, and reordering can never re-address calls, which is exactly when
    that starts to matter.
  - **An explicit setting always overrides** the derived default, except that
    an id-addressed framing can't go below `require`.
  - The framing's [profile](../schema-compatibility.md#encoding-profiles) says
    how it addresses calls: its `calls` fact gains a third value, `by_id`,
    beside `by_index` and `by_name`.
- **Ids are all or none, per protocol.** If any function in a protocol has
  `@id`, all must. A partial set is an error, which `write` fills in. Explicit
  and positional ids then never collide, and no function's id depends on its
  neighbours.

  - **The source stays the single truth.** A hidden ledger of assigned ids in
    the store was rejected: a fresh checkout, or a peer with a different
    history, could assign different ids from the same schema.
  - **CI never edits sources.** A locked or CI build doesn't write; it fails,
    listing the functions missing an id. The language server offers the same
    assignment as a quick fix.
- **Reuse is guarded.** The store keeps previous versions, so core knows which
  function each id belonged to before.
  - Reusing an id that used to mean a different function is an error: the
    same bytes would silently mean a different call.
  - Removed ids stay retired.
  - A rename keeps its id, so it isn't treated as a removal plus an addition.
- **Field ids are a later follow-up.** Struct fields can use the same mechanism.
  A `msgpack@2` keyed by field id
  ([runtime#16](https://github.com/ComlineProject/runtime/issues/16)) would
  then tolerate added and removed fields like JSON while staying nearly as
  compact as today's positional encoding.

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
