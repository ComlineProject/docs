# comline inspect

```
comline inspect [--json]
```

`comline inspect` shows what each protocol speaks on the wire and which
[guarantees](../../guide/idl/protocol.md#giving-up-a-guarantee) it keeps. Like
`comline check`, it compiles the package and writes nothing to `.comline/`.

## What it shows

For each protocol, the package's own and then its dependencies':

- **The choices:** the format, framing and handshake it resolves to, their
  parameters, and where each came from.
- **The guarantees:** schema agreement, encoding agreement, encoding
  conformance and version honesty. Each one is held or given up. A given-up
  one shows the cause and whether it's been accepted. The protocol's
  `@unverified` reason is shown with its choices.
- **The compatibility facts**, for your own protocols, once the package has
  been built: its path, line, shape hash and each function's since, as the
  latest build records them, keyed by `namespace::Protocol` ([Compatibility facts](../versioning.md#compatibility-facts)).
  They're of the latest build, not of unbuilt edits.

### Where a choice comes from

| Shown as | JSON `source` | Meaning |
|---|---|---|
| `from @framing`, `from @handshake` | `annotation` | The protocol's own annotation. |
| `from config.idp ...` | `package_default` | The package's `wire.format`, `wire.framing` or `handshake` ([Wire defaults](../../guide/packages/index.md#wire-defaults)). |
| `core's default` | `core_default` | Nothing named one, so core's default applies: `packed@1`, `datagram@2`, `comline@1`. |
| `JSON-RPC's format` | `framing` | The framing is JSON-RPC and the package names no format, so the format is JSON. |

A dependency's protocol shows its own package's defaults, not yours.

### Why a guarantee is given up

The causes are core's, the same ones `comline check` reports:

- `handshake `none``: no handshake, so neither agreement is checked.
- `handshake `<name>` doesn't establish it`: the handshake's profile doesn't
  state that guarantee.
- `framing `<name>` ships no conformance vectors` (or `format`): nothing proves
  an implementation encodes what the name promises.

What the official encodings state and establish is listed in
[Official encodings](../wire/official-encodings.md).

### Who has accepted it

A consumer accepts what a dependency's `@unverified` protocol gives up under
that dependency in its own `config.idp` (`accept_unverified`). So:

- For a **dependency's** protocol, you're the consumer. It shows
  `accepted by <your package>`, or `not accepted`, which `comline check`
  refuses.
- For your **own** protocols, the consumers are other packages, which this
  one can't see. It shows that acceptance is up to each consumer.

## Example

```
$ comline --plain inspect
protocol api::Orders (shop)
  format     packed@1                 core's default
  framing    datagram                 from config.idp `wire.framing`
  handshake  comline@1                core's default

  schema agreement       held
  encoding agreement     held
  encoding conformance   held
  version honesty        held

  api::Orders as of build 0.2.0-dev.1
  line       0.2.0
  shape      5a13d1c49ddfb76184bfe703563fa91bd772175ee15baf65244bf4f16be339cd
  since      place                    0.1.0
  since      cancel                   0.1.0
  since      track                    0.2.0

protocol api::Legacy (shop)
  format     json@1                   JSON-RPC's format
  framing    jsonrpc (method_names = qualified) from @framing
  handshake  none                     from @handshake
  unverified "the 2009 gateway can't run a handshake"

  schema agreement       given up
      because handshake `none`
      acceptance: up to each consumer's config.idp
  encoding agreement     given up
      because handshake `none`
      acceptance: up to each consumer's config.idp
  encoding conformance   held
  version honesty        held
```

The report goes to stdout. Without `--plain`, held and given-up rows are
marked and coloured.

## JSON

`--json` prints the same as `{ "protocols": [...], "facts": {...} }`. Each
protocol looks like this:

```json
{
  "package": "shop",
  "dependency": false,
  "schema": "api",
  "name": "Legacy",
  "format": { "value": "json@1", "params": {}, "source": "framing" },
  "framing": { "value": "jsonrpc", "params": { "method_names": "qualified" }, "source": "annotation" },
  "handshake": { "value": "none", "params": {}, "source": "annotation" },
  "unverified": true,
  "guarantees": [
    {
      "guarantee": "schema_agreement",
      "held": false,
      "causes": ["handshake `none`"],
      "reason": "the 2009 gateway can't run a handshake",
      "acceptance": { "state": "unknown" }
    },
    ...
  ]
}
```

`acceptance` is `{ "state": "not_needed" }` for a held guarantee, `unknown`
for your own protocol's, `not_accepted`, or
`{ "state": "accepted", "by": "<package>" }`.

`facts` is the latest build's compatibility facts, or `null` before the first
build:

```json
{
  "id": "3f2a9c41d07e4b1c8a65f2e0d91b7c34",
  "version": "0.2.0-dev.1",
  "protocols": [
    {
      "path": "api::Orders",
      "namespace": "api",
      "name": "Orders",
      "line": "0.2.0",
      "shape_hash": "5a13d1c4…",
      "functions": [
        { "name": "place", "since": "0.1.0" },
        { "name": "cancel", "since": "0.1.0" },
        { "name": "track", "since": "0.2.0" }
      ]
    }
  ],
  "encodings": [
    { "kind": "format", "name": "packed@1", "params": {}, "param_hash": "…" },
    ...
  ]
}
```

## In the editor

Hovering a protocol's name, its `@framing` or its `@handshake` in VS Code
shows the same summary as tables. The language server compiles the package
from disk for it, so it reflects the last save.

## Not shown

A dependency's compatibility facts aren't shown: they belong to its own
package. Comparing the facts of two packages or versions is left to
`comline diff` and to the handshake
([runtime#15](https://github.com/ComlineProject/runtime/issues/15)).
