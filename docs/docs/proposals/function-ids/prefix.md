# Proposal B — a prefix on the declaration

Status: **rejected**: new grammar for a form found nowhere else in the
language, and settings can't govern it; [Proposal A](annotation.md) reads like
the rest · See the [section overview](index.md) for the question both answer

**The idea:** the id leads the declaration, as in the 2024 proposal
(`proposals/idl/protocol_provider_and_provenance.ids`, `1# function
fetch_articles()`).

## Shape

```ids
@provider = Server
2# protocol LoginServerbound {
    0x00# function hello(protocol_version: u32, name: string);
    0x02# function acknowledged();
}
```

## The case for it

- **It reads like a packet table.** Ids line up down the left edge, the way
  packet tables are written in C headers and protocol specifications, and the
  way people review them.
- **It marks identity as identity.** The id is part of the declaration, not a
  setting attached to it. Under a packet framing that's what it is.
- **Prior art in Comline itself:** it's the form the project's original
  proposal used.
- **It's compact.** One line per packet in a long table.

## The case against

- **New grammar** for function and protocol declarations, and new handling in
  the formatter, the language server and the semantic highlighting.
- **Settings can't govern it** without a special case, since it isn't an
  annotation.
- **It's unusual.** Newcomers meet a `#` form found nowhere else in the
  language, and need it explained. (`#` isn't otherwise used in `.ids` files.
  The 2024 proposal also wrote annotations as `#key=value`, a form the language
  later replaced with `@`.)
- **It's harder to extend.** If ids ever needed qualifying, per phase say, a
  prefix has less room than an annotation's value.

## When this would be the right call

If packet protocols are a central use, and their tables are read and reviewed
as tables in the schema itself.
