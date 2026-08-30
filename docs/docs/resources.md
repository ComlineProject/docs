# Resources

## Comline repositories

| Repo | What |
|---|---|
| [`ComlineProject/core`](https://github.com/ComlineProject/core) | the compiler, IR, `.comline/` store, diff & auto-versioning |
| [`ComlineProject/cli`](https://github.com/ComlineProject/cli) | the `comline` CLI — `build`, `generate`, `diff`, `clean`, `reset` ([full guide](https://github.com/ComlineProject/cli/blob/main/docs/cli.md)) |
| [`ComlineProject/comline`](https://github.com/ComlineProject/comline) | runtime experiments |
| [`ComlineProject/comline-vscode`](https://github.com/ComlineProject/comline-vscode) | VS Code extension |
| [`ComlineProject/language-server`](https://github.com/ComlineProject/language-server) | LSP server |
| [`ComlineProject/package-registry`](https://github.com/ComlineProject/package-registry) · [`-frontend`](https://github.com/ComlineProject/package-registry-frontend) | package registry (server + web) — early |
| [`ComlineProject/distributions`](https://github.com/ComlineProject/distributions) | OS / distro packaging |

Publishing tooling (`comlinepm`) lives in the package-management sources; see
[Packages & dependencies](guide/packages/index.md#publishing-planned).

## Prior art

Schema / IDL / RPC systems Comline compares against or borrows from:

- [Protocol Buffers](https://protobuf.dev/) — schema + gRPC
- [Cap'n Proto](https://capnproto.org/) — zero-copy successor to Protobuf
- [Fuchsia IDL (FIDL)](https://fuchsia.dev/fuchsia-src/get-started/sdk/learn/fidl) — Fuchsia's IPC interface language
- [Apache Avro](https://avro.apache.org/) — schema-driven serialization with dynamic typing
- [Apache Thrift](https://thrift.apache.org/docs/idl) — cross-language services
- [MIDL](https://learn.microsoft.com/en-us/windows/win32/midl/midl-start-page) — Microsoft's IDL for COM / RPC
- [OpenRPC](https://open-rpc.org/) · [JSON-RPC](https://www.jsonrpc.org/) — call formats a Comline [runtime](guide/runtime/call-system.md) can speak
- [MessagePack](https://msgpack.org/) — a compact binary serialization Comline can target

## Background

- [Git Internals — Git Objects](https://git-scm.com/book/en/v2/Git-Internals-Git-Objects)
  — the content-addressable model behind the
  [`.comline/` store](guide/ir/cas.md)
