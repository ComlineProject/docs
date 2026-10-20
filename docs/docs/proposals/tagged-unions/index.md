# Tagged unions

> **Under discussion, leaning towards [Proposal A](union-declaration.md):** a
> `union` declaration whose members are written like struct fields, tagged
> with `@id`. More arguments are being gathered before deciding.

**The question.** A value that is *one of several shapes*, with a tag saying
which, is everywhere: sub-packets picked by a sub-type byte
([packet dispatch](../packet-dispatch.md#sub-packets-are-tagged-unions)), an
entity action that is attack, interact or interact-at, a result that is a
success or a failure. **Is that a feature of `enum` or of `union`?**

Where things stand:

- **`union` exists only inline and untagged,** as `union(string u32)`.
  TypeScript guesses which member arrived from its JSON kind, and the Rust
  generator refuses it
  ([comline-rust#51](https://github.com/ComlineProject/comline-rust/issues/51)).
- **Enums are bare variants** that travel by name.
- **Both need explicit numeric values on a packet wire:** phases need them for
  enums, packets for tags.
  [core#126](https://github.com/ComlineProject/core/issues/126) says the two
  should share one mechanism.

Three proposals answer the question, written to the same shape. Tracked in
[core#126](https://github.com/ComlineProject/core/issues/126).

| | Shape | In one line |
|---|---|---|
| [Proposal A](union-declaration.md) | `union EntityAction { attack: Attack … }` | a `union` declaration; members written like struct fields, tagged with `@id` |
| [Proposal B](enum-variants.md) | `enum EntityAction { Attack(target: u32) … }` | enum variants carry data, as in Rust and Swift |
| [Proposal C](both.md) | both of the above | `union` for "one of these types", enums that may carry data |

## How they compare

| | A `union` declaration | B enum variants with data | C both |
|---|---|---|---|
| Enums stay plain named values (phases, `@open`, C-style) | yes | no: rules must forbid data where it can't be | no |
| Constructs for "one of these" | one | one | two that overlap |
| Payload written inline | with the inline-fields addition | yes | yes |
| Generated Rust | an `enum` | an `enum` | an `enum` either way |
| Generated TypeScript | a discriminated union, matching the name | a discriminated union under the name "enum" | both |
| Familiar to | Protobuf (`oneof`), TypeScript, C | Rust, Swift, Kotlin | |
| The inline untagged `union(A B)` | needs a decision | unaffected | needs a decision |

All three share:
- **Explicit values with `@id`,** the same annotation as
  [function ids](../function-ids/index.md), on union members and enum
  variants alike.
- **The wire:** the tag travels before the member's fields, at the width the
  encoding states. In JSON it's an object carrying the tag and the fields; in
  `msgpack@1` it's an array.
- **Version comparison:** a changed tag is major, and adding a member is minor
  with the same caveat as enum variants. `@open` applies to unions too,
  generating an `Unknown` case
  ([schema compatibility](../schema-compatibility.md#enums)).

## Open, whichever is chosen

- **The inline untagged `union(A B)`:** keep it for JSON interop, where an
  untagged union is how many existing APIs are shaped (with an encoding
  profile fact saying which encodings support it), or retire it in favour of
  the declared tagged form.
- **Default values:** an enum field's default is its first variant today. What
  is the default of a tagged value whose members carry data?
