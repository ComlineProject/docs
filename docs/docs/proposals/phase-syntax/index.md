# Phase syntax

**The question.** [Packet dispatch](../packet-dispatch.md#phases-live-in-the-schema)
puts phases in the schema: which protocols are active in each phase, and which
packets move a connection between phases. **How are phases written?**

Packet systems are usually described by hand in three places:
- an enum of phases;
- a table of packet ids;
- a table of flows: which packet leads where, and what answers what.

Comline can state all three on the declarations themselves and generate the
tables. Two proposals answer the question, written to the same shape. Tracked
in [core#123](https://github.com/ComlineProject/core/issues/123).

| | Shape | In one line |
|---|---|---|
| [Proposal A](enum-and-annotations.md) | `enum Phase { … }` plus `@phase` and `@transition` | phases are an ordinary enum; each declaration states its own phase and transitions |
| [Proposal B](phase-block.md) | `phase Login { serverbound: […] … }` | a new declaration lists each phase's protocols and transitions in one place |

## How they compare

| | A enum + annotations | B `phase` block |
|---|---|---|
| Matches how phases are usually described | yes: an enum | partly: a new construct |
| A client-chosen next phase | natural: a field of type `Phase`, then `@transition = next` | needs a special form |
| One place shows a phase's members | through layout (one schema file per phase, with settings defaults) or tooling | yes, in the source |
| Repetition on each protocol | low with settings defaults ([core#125](https://github.com/ComlineProject/core/issues/125)) | none |
| New grammar | none, given typed annotation values ([core#124](https://github.com/ComlineProject/core/issues/124)) | a new declaration kind |
| A family in several phases | `@phase = [Login, Play]`, a list value (#124) | listed in each phase block |

Both rely on [explicit ids](../function-ids/index.md) and generate the same
dispatch tables and state machine. The difference is only where the facts are
written.
