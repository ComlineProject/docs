# Proposal A — a `union` declaration

Status: **leaning** · See the [section overview](index.md) for the question
all three answer

**The idea:** a named `union` declaration lists its members like struct fields,
`name: Type`, each tagged with `@id`. A member can also declare its fields
inline, which creates an anonymous struct.

## Shape

```ids
struct Attack {
    target: u32
}

union EntityAction {
    @id = 0x00
    attack: Attack

    @id = 0x01
    interact(target: u32, hand: Hand)       // inline fields

    @id = 0x02
    interact_at(target: u32, hand: Hand, x: f32, y: f32, z: f32)

    @id = 0x03
    swing                                    // no payload
}
```

Generated:

```rust
pub enum EntityAction {
    Attack(Attack),
    Interact { target: u32, hand: Hand },
    InteractAt { target: u32, hand: Hand, x: f32, y: f32, z: f32 },
    Swing,
}
```

```ts
type EntityAction =
  | { kind: "attack"; value: Attack }
  | { kind: "interact"; target: number; hand: Hand }
  | { kind: "interact_at"; target: number; hand: Hand; x: number; y: number; z: number }
  | { kind: "swing" };
```

## The case for it

- **Enums stay simple.** They remain named values, which is what phases
  (`@phases`), `@open`, explicit numeric values and C-style protocols need. No
  rule has to forbid data on some enums.
- **Members read like struct fields.** `name: Type` is already known, and
  Protobuf's `oneof` works the same way.
- **Tags reuse `@id`,** the mechanism functions already have.
- **The name matches the result in TypeScript,** where it's a discriminated
  union, and the word people from C and Protobuf expect.
- **A union of existing types needs no wrapper.** `value: Value` or
  `text: string` names a type that already exists, without declaring a struct
  per member.

## The case against

- **`union` would mean two things:** the inline untagged `union(A B)` and the
  declared tagged one. The inline form needs a decision (see the
  [overview](index.md#open-whichever-is-chosen)).
- **It overlaps with enums at the edges.** A union whose members all have no
  payload is an enum with extra steps. Should that be a warning suggesting an
  enum?
- **Rust users** expect data on enum variants and may look for it there
  first.
- **Inline fields are a second way to write a member's payload** beside naming
  a type. Without them, every payload needs its own struct.

## When this would be the right call

When enums should stay the plain, numeric-friendly construct that phases and
packet protocols lean on, and "one of these shapes" is worth its own word.
