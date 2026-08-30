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
    interface Message {
        receiver: string
        subject: string
        message: string
    }
    ```

=== "Luau"

    ```luau
    type Message = {
        receiver: string,
        subject: string,
        message: string,
    }
    ```
