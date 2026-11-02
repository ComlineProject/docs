# Return forms

Status: **accepted** 2026-11-02, not implemented · Quiet calls are a future
form (below) · Relates to [packet dispatch](packet-dispatch.md#replies-both-one-way-and-correlated),
[Transports](transports.md) and [bounds on types](type-bounds/max-only.md)

**The question:** a function can return a value, return `()`, or return
nothing. What does each mean, which combinations with errors make sense, and
does every framing and transport support them all?

Where things stand, checked against core:

- **The guide** says a missing return makes a call one-way, and doesn't
  mention `-> ()`.
- **`()` is accepted as a struct field, an argument and a union member,**
  where it carries no data. An array of `()` is refused
  (`validation::array-of-dataless-type`).
- **A one-way function that declares errors builds** (`function f() ! E;`),
  though with no reply, its errors can never reach the caller.
- **Framing profiles** state how calls and errors travel (`calls`, `errors`),
  not whether replies exist.
- **There's a precedent for checking a protocol against its framing:**
  `validation::reverse-calls-need-framing` refuses calls in both directions
  on a framing that can't tell requests from replies.

## Four forms

| Form | Written | On success | On failure | The caller |
|---|---|---|---|---|
| **One-way** | `function f();` | nothing | nothing | continues once the call is sent |
| **Quiet** (future) | `function f() ! E;` | nothing | an error reply | continues; a late error arrives on its own |
| **Acknowledged** | `function f() -> ();` | an empty reply | an error (`! E`), or a fault | waits until the handler finishes |
| **Value** | `function f() -> T;` | a value | an error (`! E`), or a fault | waits for the value |

- **`-> ()` means something even without declared errors:** the caller learns
  the call finished, or gets a fault if the handler failed.
- **One-way** suits events, telemetry and fire-and-forget; **acknowledged**,
  commands whose completion matters. It costs a second frame.
- **Quiet calls** reply only on failure, as memcached's quiet commands do. They
  save the reply on success but can't confirm it.

## What each framing carries

| Framing | One-way | Quiet | `-> ()` | `-> T` | `! E` |
|---|---|---|---|---|---|
| `datagram@1` (one call at a time) | yes | **no:** the caller can't tell whether to wait for a reply | yes | yes | yes |
| `datagram@2` | yes; the frame can't mark it, the schema does | possible, since request ids match a late error to its call; no runtime implements it | yes | yes | yes |
| `jsonrpc@1` | yes, as a notification | **no:** JSON-RPC forbids any response to a notification, even an error | yes, `"result": null` | yes | yes |
| Packet framings | yes | per framing | only with an acknowledgement (`@acknowledges`, or `comline.packet@1`'s control frame) | only with correlation, or a named reply packet | per framing |

## What each transport changes

| | On a reliable transport | On a transport that may lose messages |
|---|---|---|
| One-way | delivered | may be lost unnoticed: fine for telemetry |
| Quiet | errors delivered | **a lost error looks like success** |
| `-> ()`, `-> T` | delivered | a loss becomes a timeout, which the caller sees |

## The rules

1. **Framing profiles state what they carry:** a `replies` fact (none, one
   call at a time, or correlated), and whether quiet replies are supported,
   next to the existing `calls` and `errors`.
2. **The build checks each function's form against its protocol's framing,**
   as `reverse-calls-need-framing` does: `-> ()` and `-> T` need replies;
   `! E` needs a framing that carries errors.
3. **`function f() ! E;` is a build error for now:** no framing and runtime
   support quiet calls yet, so the message suggests `-> ()`. It becomes the
   quiet form on framings that declare support, once one does.
4. **[Transport fit](transports.md):** a quiet call needs reliable delivery,
   from the transport or the framing. A one-way call over a transport that may
   lose messages is allowed; hover says it may be lost.
5. **`()` only as a return type.** As a field, an argument or a union member
   it's a build error; for "maybe nothing", use `optional`.
6. **The guide documents the forms** and what each framing carries.

Suggested diagnostic codes: `validation::one-way-cannot-raise`,
`validation::unit-outside-return`, `validation::replies-need-framing`,
`validation::errors-need-framing`.

## Open

- **Quiet calls in generated code:** how a late error reaches the caller (a
  callback, a stream of errors, the next call's result), and how a caller
  learns earlier quiet calls succeeded (memcached sends a no-op and waits for
  its reply).
- **Packet framings:** whether a named reply packet (`@reply`) is how `-> T`
  is written there, designed with [packet dispatch](packet-dispatch.md).
- **The facts' names and values** in the framing profiles.
