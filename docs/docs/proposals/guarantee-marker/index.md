# Marking a given-up guarantee

**The question.** An extension can leave one of Comline's guarantees between
peers unestablished, and the author then vouches for what replaces it. The
guarantees are schema agreement, encoding agreement, encoding conformance and
version honesty; see [Extending the call system](../extensibility.md#giving-up-a-guarantee).
That takes an explicit marker in the schema, playing the role `unsafe` plays in
Rust. **What should the marker say, and how?**

The rules around the marker are settled independently and hold for every option
below:
- a mandatory reason;
- off by default, gated through `settings`;
- an error when it's missing and a warning when it's needless;
- consumers accept it per protocol;
- visible everywhere;
- a major bump when added.

The first candidate, `@unchecked`, raised the objection that it doesn't say
*who* doesn't check *what*. Four proposals answer it, written to the same shape
so they can be read side by side. Tracked in
[core#121](https://github.com/ComlineProject/core/issues/121).

| | Marker | In one line |
|---|---|---|
| [Proposal A](waives.md) | `@waives(schema_agreement = "…")` | names each guarantee the author knowingly gives up |
| [Proposal B](assumes.md) | `@assumes(schema_agreement = "…")` | names what the author assumes holds in place of Comline's check |
| [Proposal C](unverified.md) | `@unverified = "…"` | one marker; core works out which guarantees are affected |
| [Proposal D](unchecked.md) | `@unchecked = "…"` | the original name, kept |

## Two choices, not one

The options mix two independent decisions:

1. **Does the marker name the guarantee?** A and B do; C and D don't, and leave
   core to infer it from the handshake and encodings in use.
2. **Which word?** *waives*, *assumes*, *unverified* or *unchecked*.

The first decision decides more than the second:
- **Consumers:** whether they accept a protocol as a whole or each guarantee it
  gives up.
- **Cross-checking:** whether core can compare what the author declared with
  what the protocol actually gives up.
- **Syntax:** how much syntax work is needed (see below).

A word can be paired with either answer, for example `@unverified(schema_agreement
= "…")`. So a decision can take the shape from one proposal and the word from
another.

## How they compare

| | A `@waives(…)` | B `@assumes(…)` | C `@unverified` | D `@unchecked` |
|---|---|---|---|---|
| Says **what** is given up, in the schema | yes | yes | no, core infers it | no, core infers it |
| Says **who** carries it | the author waives | the author assumes | implied | implied |
| Consumers accept **per guarantee** | yes, in the syntax | yes, in the syntax | only if acceptance tracks the inferred set | same as C |
| Core can catch a mismatch between declared and actual | yes | yes | nothing declared to mismatch | same as C |
| Reads clearly to a newcomer | legal register, but precise | clear; direction can be misread | clear | familiar from Rust and Swift; collides with Comline's other "checks" |
| Works with today's annotation syntax | no: a keyed value is new | no: same | yes: a plain string | yes: a plain string |
| Package-level cases (`config.idp`) read the same | yes | awkward for version honesty | yes | yes |

**On syntax.** An annotation's value is a scalar today, and a list annotation is
parsed as validator calls (`@validators = [StringBounds(…)]`). Naming the
guarantee therefore needs a new form: either a keyed annotation value as shown
in A and B, or one annotation per guarantee
(`@waives.schema_agreement = "…"`). That is core grammar work, and it's the
same work for A and B.

## Open across all four

- How the call-site skip in the runtimes is named once the word is chosen:
  `Client::new_unchecked`, or something descriptive like
  `Client::without_handshake`.
- Whether the guarantee names become a fixed vocabulary in core, so diagnostics,
  hover text and acceptances all use the same four words.
