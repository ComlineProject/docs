# Bounds on types

Status: **accepted 2026-11-02; steps 1–6 shipped, 7–12 in progress** ·
[core#98](https://github.com/ComlineProject/core/issues/98) · Decided through
[the proposals](../proposals/type-bounds/index.md):
[Proposal D](../proposals/type-bounds/max-only.md), with
[strings as `char[]`](../proposals/type-bounds/char-strings.md) and
[how bounds work](../proposals/type-bounds/model.md)

A **bound** is a maximum on how big a value can be, written in its type. It's
checked while decoding, so a decoder refuses an oversized value before
allocating it. This page is the decided design and its rollout; the proposals
hold the reasoning and the alternatives.

## The design

### Syntax

- **Every bound is `T[max N]`:** at most N items. `T[N]` stays exactly N.
- **Strings are arrays of `char`,** one Unicode scalar value each, always sent
  as text. A string of at most 64 characters is `char[max 64]`; exactly 2,
  `char[2]`.
- **`string` is the built-in name for `char[]`:** a string at the package's
  default maximum. `string[max 10]` is a list of 10 strings.
- **`max` is a keyword only right after `[` in a type;** everywhere else it
  stays a name.
- **A bound may be a constant:** `char[max MAX_NAME]`, any unsigned integer
  constant, stored resolved.
- **Only a maximum.** Minimums ("not empty", "at least one") and integer value
  ranges are validators.

```ids
type AccountName = char[max 32]

struct Customer {
    @validators = [NonEmpty()]
    name: AccountName
    tags: char[max 32][max 10]
}

struct OrderLine {
    sku: char[8]
}
```

### Which types, where

- **Strings and dynamic arrays** take a maximum. Integers, floats, `bool`,
  enums, structs, unions and `()` don't.
- **No suffix after a bounded alias where it's used:** for an alias of `char[]`
  or `T[]`, `[…]` at a field, parameter, return or union member is an error; the
  limit changes in the alias, and a list of it is its own alias. Aliases of
  numbers and structs keep the suffix; `string` is exempt.
- **`max 0` is an error,** and so are an exact length of 0 and any negative
  size; core caps a maximum at `u32::MAX`.
- **One stored form for strings:** `string`, `char[]`, `char[max N]` and
  `char[N]` all resolve to a string with an optional maximum or exact length.
- **A single `char` literal is `"a"`,** checked to be exactly one character.
- **Validators ignore bounds when matching:** `for string` applies to every
  string, `for u32[]` to every `u32[max N]`.

### No unbounded value

Every string and dynamic array, at any position, has a maximum from, in order:

1. the position itself;
2. a default from any `settings` layer (package, schema, preset), merged as
   settings are, stored resolved at each position it reaches;
3. a give-up, `@unverified = "reason"`.

A type that can contain itself needs a depth limit from the same three sources
(`@max_depth`). Every message then has a computable worst-case size per format,
and a worst-case size in memory per target.

- **A package default reaches only its own positions.** A dependency's types
  keep the maximum resolved in the dependency; std bounds its own strings.
- **Only the resolved maximum counts:** `string` at a default of 64 and
  `char[max 64]` are the same type to version comparison.
- **The rule applies to the version being built,** not to stored history.
- **Giving up "bounded size"** goes through the `@unverified` rules: enabled in
  settings, accepted by consumers per protocol, a major bump when added.

### What's checked, and where

| Where | What |
|---|---|
| Build | `max 0`; a constant named `max` used as a length; a value breaking a bound (defaults, constants); a validator's minimum above the type's maximum (error) or a validator capping below it (warning); untagged union members differing only by bound; worst-case wire sizes against each framing's default frame limit and every configured one; worst-case memory per target against its budget |
| Generating | a target supports the full declared maximum and depth or refuses to generate, naming the target (generators configure their parsers' depth); a generator that doesn't declare the bounds feature is refused |
| Handshake | the compatibility facts (`comline@2`) carry each position's resolved maximum |
| Sending | an encoder never produces bytes a conforming decoder refuses: out-of-bound values fail locally |
| Receiving | decoders refuse out-of-bound values while decoding, before allocating where the format allows; validators, on by default, run after |
| Connecting | the shared runtime core refuses a connection configured below a protocol's worst-case message, unless given up |

### On the wire

The bytes don't change; only what a decoder accepts does.

| Format | Array of at most N | String of at most N characters |
|---|---|---|
| `packed@1`, `msgpack@1` | a count above N is refused before allocating | a byte length above 4 × N is refused before allocating; characters are counted during the strict UTF-8 check |
| `json@1` | refused at item N + 1 | counted after unescaping |

A single `char` is sent per format at no size or speed cost: raw UTF-8 in
`packed@1`, a one-character string in `msgpack@1` and `json@1`. An array of
`char` is always text: `char[N]` sends a byte length too, unlike other fixed
arrays in `packed@1`. Text is never normalized; what's sent is what's counted.

### Version comparison

Any change to a bound is breaking: tightening breaks old senders, loosening old
receivers. Adopting a maximum is breaking too, accepted before 1.0.

### Validators

- **Enforced by default.** `validate_on_decode` defaults to checking; turning it
  off is an explicit give-up with a reason.
- **std gains** `NonEmpty`, `MinChars`, `MinItems` and `IntRange`.
  `StringBounds.max_chars` defaults to `u32::MAX`, then is deprecated.
- **Generators build the std minimum validators into the decoder,** at a
  bound's cost.

### Generated code

1. **Always:** the language's native string or list, checked. Free unless a
   string is near its limit, since a character takes at least one byte and one
   UTF-16 unit.
2. **Named aliases:** a checked type of their own (a newtype, a branded type),
   so a wrong value can't be built.
3. **Opt-in:** fixed-capacity storage, in the consumer's generator
   configuration.

A generator setting keeps plain types (level 1 for aliases too) while
consumers migrate; decoding still checks.

A single `char` maps to a code-point type where a language's own `char` is a
UTF-16 unit (`int` in Java, `Rune` in C#).

### Written once

The rule lives in core's stored schema and the codegen kernel's plan; each
language implements a small checking primitive; conformance vectors pin the
edges (at the limit, one over, multi-byte characters near it, a prefix just
over 4 × N); differential fuzzing proves every language agrees. A shared
runtime core primitive is used only where measurement shows it's faster.

### Tooling

- **Hover:** a bound in words, outer to inner; each type's smallest and
  worst-case size per format; and per configured target, the generated type,
  its size where fixed, and whether the target supports the maximum.
- **A lint** suggests an alias past two bounded levels.
- **Migration:** `comline` lists every unbounded position and offers to add a
  package default, from the author's input, never guessed.

## Not part of this decision

- **[Transports](../proposals/transports.md):** a separate draft; bounds work
  with framings and configured limits without it.
- **C text** (`c_char`, `c_byte`) belongs to
  [Comline for systems software](../proposals/systems-software.md).

## Rollout

| Step | Repository | Work |
|---|---|---|
| 1 | core | grammar: `T[max N]`, `char`, `max` as a keyword after `[` only, constants as bounds; the alias-suffix rule; negative and zero sizes refused |
| 2 | core | the stored schema: a maximum per position, unbounded positions byte-identical to today; settings defaults and `@max_depth` resolved |
| 3 | core | build checks (the table above), and the unbounded-position listing for migration |
| 4 | core | version comparison: bound changes breaking |
| 5 | core, std | `NonEmpty`, `MinChars`, `MinItems`, `IntRange`; `StringBounds.max_chars` default |
| 6 | core, generation | the doc model and the codegen kernel carry bounds; generators declare the bounds feature, and the CLI refuses those that don't |
| 7 | runtime | conformance vectors for bounds per format, the depth limit, and bounds in the compatibility facts |
| 8 | comline-rust | checks while decoding and encoding, alias newtypes, validators on by default |
| 9 | comline-typescript | checks while decoding and encoding, branded aliases; validators with core#96's step 4d |
| 10 | cli | `validate_on_decode` default, worst-case sizes against configured limits, migration |
| 11 | language-server | hover sizes and cost per target, the nested-bounds lint |
| 12 | docs | the guide: bounds, `char`, and the migration |
