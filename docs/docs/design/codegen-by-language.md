# Codegen by language

Status: **sketch** — worked examples of how one schema should surface in each
language. Not normative; `rust` is the only generator implemented today (see
[Generating code](../guide/codegen/generating-code.md)).

From this schema:

=== "IDL"

    ```ids
    struct Message {
        receiver: String
        subject: String
        message: String
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
