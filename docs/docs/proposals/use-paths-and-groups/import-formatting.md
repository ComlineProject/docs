# Import formatting

Status: **accepted** · decided with the user 2026-11-15 · part of [Own schemas,
provenance and dependency groups](index.md)

**The question.** A file's `use` lines have no set order, so each author orders them their own way, and a diff mixes
real changes with reordering. Now that a path says where a schema comes from
([relative paths](relative-use.md)) and dependencies can have [groups](dependency-groups.md), **what order is the
default, and can a project change it?**

## The default order

**Decided.** The language server's formatter, and any `comline fmt`, put a file's imports in tiers:

1. **`std`**: `use std::…`
2. **the package's own**: `use package::…`, `use parent::…`, `use self::…`
3. **dependencies**: every other `use`

Within the dependencies tier, **groups come in first-declared order** (the order of each group's first entry in
`config.idp`, see [Dependency groups](dependency-groups.md#order)), **then ungrouped dependencies**. Within a tier
(and within a group), imports are **alphabetical** by path.

```ids
use std::http::Request
use std::validators::{NonEmpty, MinChars}

use package::types::{Customer, Order}
use parent::common::Error

use logging::Logger
use metrics::Counter

use shared_types::foo::X

use net::Client
```

Here `logging` and `metrics` are in the group `platform`, declared first; `shared_types` is in `team`; `net` has no
group. A blank line separates tiers, and separates groups inside the dependencies tier, the way the example shows.

**Decided: a group orders dependencies only.** `std` is always a tier of its own, placed by `imports.order`; a group
can't sort before it or between the tiers.

The formatter doesn't change what an import means: it only reorders `use` statements.

## Configuring it

**Decided.** The order is configurable in a `[format]` table:

```toml
[format]
imports.order = ["std", "package", "dependencies"]
```

`imports.order` lists the tiers, each once, in the order they are written: `std`, `package` (the package's own) and
`dependencies`. The default is the order above. Putting `dependencies` first is
`["dependencies", "std", "package"]`. The list is read strictly (a proposed detail): a tier left out, repeated or misspelt is
an error, so a typo doesn't quietly reorder every file.

### Where the configuration lives

**Decided: [`comline.toml`](../../reference/package/comline-toml.md), not `config.idp`.**

- `config.idp` is **frozen into every build and hashed**. It holds what a package *is*: its identity, what it
  depends on, how it is put on the wire. An import order is how a file is *written*; putting it there would make
  reordering a style setting a change to the frozen config, to every hash that covers it, and potentially to the
  package's history. The same reasoning kept groups out of every hash.
- `comline.toml` is **tooling configuration**: consumer-owned, committed, never frozen and never part of a published
  package, and it already holds the tools' tables (`[generate]`, `[doc]`). `[format]` is another.
- Nothing downstream has to read it: a dependency's formatting is its authors' business, and a package's consumers
  never see it.

The alternative, a `format` key in `config.idp`, would be read by the same tools and would travel with a published
package. It was not taken.

### Precedence

**Decided:** the project's `comline.toml`, then the defaults. Each is applied key by key, like
[`[generate]`](../../reference/package/comline-toml.md#precedence).

**Decided: no per-user override.** `comline.toml` is the project's, committed beside the package, so the project's
`[format]` is what every author's editor formats with, and a save in one editor never makes a diff in the next.

## Who reads it

- **The language server's formatter**, in the editor, on a format request. It reads `[format]` from the `comline.toml`
  beside the package, with or without the `#:schema` line, as it already checks the file.
- **Any `comline fmt`.** There is no such command today; if one is added, it reads the same table with the same
  function. The ordering lives in core, over the parsed `use` statements, so the two can't disagree, and a conformance
  case in the specification repository (a schema, a configuration, and the text it must format to) holds every
  implementation to it.

`comline.toml` gains the table in its [reference](../../reference/package/comline-toml.md) and in the JSON Schema served
for it, so an editor completes `imports.order` and checks its values.
