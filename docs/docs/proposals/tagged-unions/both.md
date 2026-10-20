# Proposal C — both

Status: **under discussion** · See the [section overview](index.md) for the
question all three answer

**The idea:** a `union` declaration for "one of these existing types"
([Proposal A](union-declaration.md)), and enum variants that may carry data
([Proposal B](enum-variants.md)). Each construct covers the cases it reads
best for.

## Shape

```ids
union Value {
    @id = 0
    text: string
    @id = 1
    number: s64
}

enum EntityAction {
    @id = 0x00
    Attack(target: u32)
    @id = 0x01
    Swing
}
```

## The case for it

- **Each reads best for its own cases:** a union of existing types without
  wrappers, and an enum whose variants mostly have no data but some do.
- **Users from either background** find what they expect.

## The case against

- **Two ways to say the same thing.** Every schema author has to choose, and
  reviewers and style guides have to settle which is preferred.
- **Everything is specified twice:** wire, version rules, generators, `@open`,
  explicit values.
- **It inherits B's cost** of rules forbidding data on phase and C-style enums.

## When this would be the right call

When real schemas turn out to need both shapes often, and the cost of two
constructs is smaller than forcing one into the other.
