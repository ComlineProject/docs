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
    comline-typescript#5, #8) — `struct` becomes `export interface`; `error`
    an `export interface` (wire payload) plus an `export class <Name>Error`
    throwable; `enum` an `export enum` with string values. A `protocol` emits
    the full RPC shape against `@comline/runtime`: an `IR_HASH` (the canonical
    `schema_ir_hash`, so a TS peer and a Rust peer agree), `<Proto><Fn>Params`
    interfaces, a provider interface of `Promise`-returning methods, a
    `<PROTO>_CALLS` table, a `<Proto>Dispatcher`, a `<Proto>Client` (+ static
    `connect`), and a `serve<Proto>` helper — framing from `@framing` / the
    package default. `lib` mode (comline-typescript#9) wraps the per-schema
    output in an npm package — `package.json` (declaring `@comline/runtime`),
    `tsconfig.json`, and a `src/index.ts` barrel.

=== "Luau"

    ```luau
    type Message = {
        receiver: string,
        subject: string,
        message: string,
    }
    ```
