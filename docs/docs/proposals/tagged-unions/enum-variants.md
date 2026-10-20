# Proposal B — enum variants that carry data

Status: **under discussion** · See the [section overview](index.md) for the
question all three answer

**The idea:** an enum's variants can carry data, as in Rust, Swift and Kotlin's
sealed classes. This is the 2024 `enum_variant_associated_kind` proposal; the
[enum guide](../../guide/idl/enum.md) already mentions it
(`Encrypt(EncryptionAlgorithm)`).

## Shape

```ids
enum EntityAction {
    @id = 0x00
    Attack(target: u32)

    @id = 0x01
    Interact(target: u32, hand: Hand)

    @id = 0x02
    InteractAt(target: u32, hand: Hand, x: f32, y: f32, z: f32)

    @id = 0x03
    Swing
}
```

The generated Rust is the same as [Proposal A](union-declaration.md)'s.

## The case for it

- **One construct** for "one of these", whether the variants carry data or
  not.
- **It mirrors the generated Rust** exactly, and reads naturally to Rust, Swift
  and Kotlin users.
- **Payloads are inline,** with no extra struct per variant.
- **It continues an existing proposal,** already pointed to from the guide.
- **Adding data to one variant later** is a change to the same declaration,
  not a move from `enum` to `union`.

## The case against

- **Enums get harder.** A `@phases` enum, an enum with explicit numeric values
  on a packet wire, or a C-style enum must not carry data, so rules have to
  forbid it in those places.
- **"Enum" means named numbers** to people coming from C, C++, Protobuf, Java
  and TypeScript.
- **TypeScript** renders it as a discriminated union, not a TS `enum`, so the
  generated code's shape doesn't match the schema's word.
- **The untagged inline `union(A B)` stays** beside it, so "one of these"
  still has two spellings with different wire behaviour.

## When this would be the right call

When the audience is mainly Rust-like and one construct for all sum types
matters more than keeping enums plain.
