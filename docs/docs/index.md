# Welcome to Comline

!!! warning "Early days"
    Comline is in heavy development and changes constantly. Much of this
    documentation is working design material rather than a polished reference —
    parts are dense and read closer to notes than prose. It will be rewritten
    for people, end to end, once the design settles.

Comline is an agnostic schema, RPC/IPC (or any other similar terminologies)
library, similar to ones like:

 - [Protobuf](https://protobuf.dev/), [Capn'Proto](https://capnproto.org/), [Fuchsia IDL (FIDL)](https://fuchsia.dev/fuchsia-src/get-started/sdk/learn/fidl)
 - [Apache Avro](https://avro.apache.org/), [Apache Thrift](https://thrift.apache.org/docs/idl)


## What constitutes Comline?

### [Interface Definition Language (IDL or also named Schema)](./guide/idl/index.md)
Some of the distinct differences to other libraries is that this
[IDL/Schema](./guide/idl/index.md) allows to be more flexible, optional or robust, 
detailed and specific when setting options, rules, message structures,
protocols (named services in protobuf, interfaces in capn'proto) and so on...


### [Intermediate Representation (IR)](./guide/ir/index.md)
Schemas compile into an Intermiate Representation that solidifies the structure as a sort of "mini-spec",
which then can output to other formats like a rpc schema such as
[OpenRPC](https://open-rpc.org/), a custom text format, or better a binary
compact format like [msgpack](https://msgpack.org/) which is ideal to reduce wire load


### [Code Generation (Codegen)](./guide/codegen/index.md)
Codegen is a common feature that similar libraries have, however
some of them lack details at development time and might make the experience
more indicated towards "try-it-out" and not provide so much detail,

Comline tries to provide more language specific generation that fits as best,
detailed and information specific to them as possible, be it for compiled
or dynamic languages, it's believed to be important to have as much information
detail as possible at development type.


### [Runtime & call system](./guide/runtime/index.md)
A runtime handles transport, message parsing and routing a call to its
implementation. The **call system** part of it is pluggable: specs like
[json-rpc](https://www.jsonrpc.org/) can be used, or a custom format that is
binary compact like msgpack, or any custom call format you need to implement.

The message serialization is likewise specifiable, so you can use any data
format, from JSON to other schema libraries' formats, or once again binary
minimalist formats like msgpack.
