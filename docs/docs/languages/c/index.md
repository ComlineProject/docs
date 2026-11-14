# C

There is no C generator yet, so nothing turns a schema into C types and
codecs. What C has is the runtime's protocol core, `comline-runtime-ffi`,
through its [C ABI](../../reference/languages/c-abi.md): the handshakes, the
connection framings, envelopes, connection state and frame limits. Codecs,
transports and dispatch are the host's to write.

It's the same core the TypeScript runtime loads through wasm, so a host on it
speaks the same bytes as the Rust and TypeScript runtimes.
