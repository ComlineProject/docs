# Codegen by language

Status: **sketch** — worked examples of the **source** one schema should produce
in each language ([codegen](generation.md#vocabulary), not the libgen packaging
around it). Not normative; `rust` is the only generator implemented today (see
[Generating code](../guide/codegen/generating-code.md)).

From this schema:

=== "IDL"

    ```ids
    struct Message {
        receiver: string
        subject: string
        message: string
    }
    ```

## Compiled languages

=== "Rust"

    ```rust
    trait Message {
        fn receiver(&self) -> String;
        fn subject(&self) -> String;
        fn message(&self) -> String;
    }
    ```

## Dynamic languages

=== "Python"

    ```python
    class Message(Protocol):
        receiver: str
        subject: str
        message: str
    ```

=== "TypeScript"

    ```ts
    export interface Message {
        receiver: string;
        subject: string;
        message: string;
    }
    ```

    Implemented ([generation#4](https://github.com/ComlineProject/generation/pull/4),
    [comline-typescript#5](https://github.com/ComlineProject/comline-typescript/pull/5)) —
    `struct` / `error` become `export interface`, `enum` an `export enum` with
    string values. A `protocol` emits the RPC shape: an `IR_HASH` (the
    canonical `schema_ir_hash`, so a TS peer and a Rust peer agree), a
    `<Proto><Fn>Params` interface per function, discriminated-union error types
    from each `!` keyed by ordinal, and an `export interface` of
    `Promise`-returning methods. A `<Proto>Client` / dispatcher and a runtime
    package to link them against are the next step.

=== "Luau"

    ```luau
    type Message = {
        receiver: string,
        subject: string,
        message: string,
    }
    ```
