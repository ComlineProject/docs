# Named connections: prior art

Status: **draft** · part of [Named connections](index.md) · every claim below cites the page
it was read from, and a claim that couldn't be confirmed was left out

Two questions put to other systems:

1. **When generating code for one set of files, what happens to the services and protocols
   defined elsewhere** (imported, or in a dependency)?
2. **How is what a server exposes grouped:** by composing what the application registers, or
   by a declaration of the surface?

## protoc and Buf

- A plugin receives a `CodeGeneratorRequest` with two lists. `file_to_generate` is "the
  .proto files that were explicitly listed on the command-line. The code generator should
  generate code only for these files." `proto_file` holds "FileDescriptorProtos for all files
  in files_to_generate and everything they import", in topological order, so the generator
  can resolve what the generated files refer to without being asked to write it. Source:
  [`plugin.proto`](https://github.com/protocolbuffers/protobuf/blob/main/src/google/protobuf/compiler/plugin.proto).
- Buf lets a plugin generate the imports too, by `include_imports`, which "generates all
  imports except for Well-Known Types" and "works the same as the `--include-imports` flag on
  `buf generate`". Source: [`buf.gen.yaml` v2](https://buf.build/docs/configuration/v2/buf-gen-yaml/).
  Its default isn't stated on that page.

## gRPC (and tonic)

- A call's target is a path, `/` Service-Name `/` method name, and for protobuf the service
  name is the optional proto package, a dot, and the service name:
  `/google.pubsub.v2.PublisherService/CreateTopic`. Source:
  [gRPC over HTTP/2](https://github.com/grpc/grpc/blob/master/doc/PROTOCOL-HTTP2.md).
- Health checking is a standard service API with an implementation supplied by a library;
  the application adds it to its server and updates its status per service name, the empty
  string standing for the whole server. Source:
  [gRPC health checking](https://grpc.io/docs/guides/health-checking/).
- In tonic, the health service comes from its own crate
  ([`tonic-health`](https://docs.rs/tonic-health/latest/tonic_health/), "a `tonic` based gRPC
  healthcheck implementation") and the server registers each service on the builder:
  `Server::builder().add_service(health_service).add_service(GreeterServer::new(greeter))`.
  Source: tonic's
  [health example](https://github.com/hyperium/tonic/blob/master/examples/src/health/server.rs).

So each service is generated from its own files, in its own library, and the application
composes them when it builds the server.

## Thrift

- The compiler's `-r[ecurse]` option is "also generate included files": generating the files
  an input includes is an option, not the default. Source:
  [`thrift(1)`](https://manpages.org/thrift). An `include` itself "adds corresponding include
  statements into the code generated for this Thrift document". Source:
  [Thrift IDL](https://thrift.apache.org/docs/idl).
- `TMultiplexedProcessor` "allow[s] a single `TServer` to provide multiple services":
  `registerProcessor(String serviceName, TProcessor processor)` registers each by name, and a
  request carries the service name and a separator before the method, which selects the
  processor; without the separator the call goes to a default processor, if one was
  registered. Source:
  [`TMultiplexedProcessor.java`](https://github.com/apache/thrift/blob/master/lib/java/src/main/java/org/apache/thrift/TMultiplexedProcessor.java).

Again, generation is per file, and the application composes at registration.

## Cap'n Proto

- A file has a unique 64-bit ID, and each type and annotation in it may have one, assigned
  automatically when omitted (the page's example gives an interface its own ID); an `import`
  expression names the scope of another file. Source:
  [Cap'n Proto language](https://capnproto.org/language.html). The page doesn't say whether
  imported files are generated.
- `capnp compile` generates files for the schema named on the command line. Source:
  [the `capnp` tool](https://capnproto.org/capnp-tool.html).
- What a connection starts from is a bootstrap capability: the client "request[s] the
  bootstrap capability from the server" (`getMain`), and the server's first constructor
  argument is any client object, which can be "a capability imported from another server",
  re-exported. Source: [C++ RPC](https://capnproto.org/cxxrpc.html).

The set of interfaces a connection exposes is a runtime object handed over at the start, not a
declaration in the schema.

## Smithy

- "A service is the entry point of an API that aggregates resources and operations together."
  Its `operations` and `resources` members bind those shapes to it, and "the closure of a
  service is the set of shapes connected to a service through resources, operations, and
  members." Shape names in the closure must be unique regardless of namespace, with conflicts
  resolved by the service's `rename` property. Source:
  [Smithy service types](https://smithy.io/2.0/spec/service-types.html).

The exposed surface is declared in the schema, and it reaches across namespaces.

## WebAssembly WIT worlds

- "A world describes a set of imports and exports." Exports are "the interfaces or functions
  provided by a component", imports those "that a component depends on", `include` pulls in
  another world's imports and exports, and `import wasi:http/outgoing-handler;` names an
  interface of another package. Source:
  [the component model's WIT page](https://component-model.bytecodealliance.org/design/wit.html).
- `wit-bindgen`'s Rust `generate!` takes the world to generate for: "the name of the world
  that bindings are being generated for", required when the package has more than one world.
  Its `with` option points interfaces at "already generated bindings", so "no bindings will be
  generated at all" for them. Source:
  [`wit-bindgen`'s `generate!` docs](https://github.com/bytecodealliance/wit-bindgen/blob/main/crates/guest-rust/src/lib.rs),
  and [the repository](https://github.com/bytecodealliance/wit-bindgen).

A declaration of the surface, in the schema, that can name other packages' interfaces, with
bindings generated per world and reuse of existing bindings as an explicit option.

## FIDL and Mojo

- FIDL files are grouped into libraries by the author, "a group of logically related
  functionality with a unique library name", and a library imports another to use its
  declarations. Bindings are spoken over a channel. Source:
  [FIDL overview](https://fuchsia.dev/fuchsia-src/concepts/fidl/overview).
- Bindings are per library: "the `fidl()` library target creates individual binding targets
  for each supported language", generated only "unless they are included as a dependency", and
  a component lists, for example, `fidl/fuchsia.examples:fuchsia.examples_rust` in its `deps`.
  Source: [Fuchsia, FIDL](https://fuchsia.dev/fuchsia-src/get-started/learn/fidl/fidl).
- What a component provides or consumes is declared outside the FIDL, in its manifest, by
  protocol name: `capabilities` with `protocol: "fuchsia.example.ExampleProtocol"`, `expose`,
  `offer` and `use`. Source:
  [protocol capabilities](https://fuchsia.dev/fuchsia-src/concepts/components/v2/capabilities/protocol).
- In Mojo, "if your Mojom references definitions from other Mojom files, you must import those
  files" ([Mojom README](https://chromium.googlesource.com/chromium/src/+/main/mojo/public/tools/bindings/README.md)),
  and C++ is emitted from each input `.mojom`; a target needing an interface depends on the
  target that generates it. A `mojo::Receiver<T>` "bridges an implementation of `T` with a
  single bound message pipe endpoint". Source:
  [Mojo C++ bindings](https://chromium.googlesource.com/chromium/src/+/main/mojo/public/cpp/bindings/README.md).

Bindings come from each library's own target, and a dependency's from its own, listed as a
dependency. What a process offers is declared outside the IDL (FIDL's manifest), or is what
the application binds to each pipe (Mojo), one implementation to one endpoint.

## Summary

| System | Generates | What a server exposes |
| --- | --- | --- |
| protoc, Buf | the files listed; imports are context, or opt-in with `include_imports` | not part of the IDL; each service registered by the application |
| gRPC, tonic | each service from its own files and library | registered one by one on the server; the full method path names the service |
| Thrift | the files given; `-r` also generates includes | a multiplexing processor, services registered by name |
| Cap'n Proto | the files named on the command line | a bootstrap capability, an object chosen at runtime |
| Smithy | n/a (a model, with generators) | a `service` shape lists operations and resources, with its closure across namespaces |
| WIT | bindings for one named world | the world: imports and exports, including other packages' interfaces |
| FIDL | bindings per library, depended on by target | a component manifest outside the IDL |
| Mojo | bindings per `.mojom` target, depended on by target | the application binds an implementation to each pipe endpoint |

The two groups:

- **Generate only your own files, and compose at registration:** protoc and Buf, gRPC and
  tonic, Thrift, Mojo, and Cap'n Proto at runtime. A service generated in another package is
  used by registering it.
- **Declare the exposed surface explicitly:** Smithy (in the schema), WIT (in the schema,
  across packages) and FIDL (in a manifest, outside the schema).

Where Comline sits today is a third place: it generates one connection from everything the
package declares, and the application can't compose a subset except by leaving the generated
entry points. The options map as follows, without anything here being a recommendation:
Option 0 and the smaller step in it are the first group's way (register what you serve); Options
1 and 2 declare the surface for one package, as Smithy does; Option 3 is WIT's.
