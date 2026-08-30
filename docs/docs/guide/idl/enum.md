# Enum

An **enum** is a closed set of named variants.

``` py linenums="1"
enum Deliver {
    To
    Reply
    Forward
}
```

Use it as a field type, optionally with a default:

``` py linenums="1"
struct Message {
    deliver: Deliver = default   // first variant, `To`
}
```

Variants are bare identifiers. Attaching data to a variant
(`Encrypt(EncryptionAlgorithm)`) is a [proposal](../../proposals/index.md), not
yet part of the language.
