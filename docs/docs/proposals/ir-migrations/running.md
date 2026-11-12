# Running a migration

Status: **draft** · part of [Migrating stored IR across format versions](index.md)

**The question.** How does a store change format without any moment at which history is lost, however the process
ends, and how does someone find out what it would do first?

## The rule

**Nothing is deleted or changed without the user doing so.** No command moves, rewrites, resets or deletes a store as a
side effect. A command that finds a store it can't use as it is *stops*, says what it found and names the command that
fixes it, and does nothing until the user runs that command. The only exception is reading: a read command may read an
old store through an in-memory migration, because that changes nothing on disk.

## What each command does with each stamp

`ensure_compatible_store` stops deleting. With the stamp *N* and a binary that writes *C*:

| The store | A read command (`diff`, `doc`, `generate`, `inspect`) | A write command (`build`, `release`, …) |
|---|---|---|
| N = C | proceeds | proceeds |
| N < C, and a chain of steps reaches C | reads through an **in-memory** migration and writes nothing | **stops**: "the store is format N; run `comline store migrate` (`--check` shows what it would do)". On a terminal it asks whether to run exactly that, and does nothing unless the user says yes; without a terminal (CI) it fails with that message |
| N < C, and no chain does (pre-1.0 only) | an error naming the format and the [options](steps.md#what-cannot-be-migrated) | **stops**, naming `comline store reset`. It never offers to reset inline |
| unstamped, or damaged | an error naming the format or the file | the same error; nothing is changed |
| **N > C** | an error: the store is format N, this comline reads up to C, and *comline ≥ X* reads N | the same error; nothing written |
| stamps or refs in conflict because Git merged stores in different formats | an error ([see Git](#git)) | the same |

Reading an old store needs no write because a migration is a pure function: a read command can run the chain on the
versions it needs and drop the result. That makes `comline diff`, `doc --version` and `generate` work on a store nobody
has migrated yet, at the cost of the memory and time of the chain, which a cache can hide.

Today's behaviors of deleting an older store and of deleting a newer one are both gone. Binaries from before this
proposal still delete a store whose stamp they don't expect; they are out of scope.

## The procedure

`comline store migrate`, which is also what `build` runs if the user confirms it:

1. **Claim the store.** `mkdir .comline.migrating/` beside `.comline/`. It fails if the directory exists, which is the
   lock. If it exists from a crash, see [below](#crashes). The migrating directory is on the same filesystem as
   `.comline/` so that the renames in step 5 are atomic.
2. **Plan, in memory.** Read the container: the refs, then every commit reachable from them by parents, second parents
   included, each object checked against its hash. Decode each version under N, run the chain, and encode the result
   to bytes, writing nothing. The plan lists the versions, the steps, the objects that change, and every unknown with its
   path and reason. `--check` stops here, after the [checks](#verifying) that don't need the disk.
3. **Write the new store** into `.comline.migrating/`: `objects/` (payloads that didn't change are linked or copied under
   the same hash; everything else is new), `refs/heads/main` with each head mapped, and `FORMAT_VERSION` **last**. A
   `JOURNAL` there records the old head hashes, the stamp and assumed format, and the state: `writing`, then `ready`.
   `deps-cache/` is not read or written: it isn't part of the store.
4. **Verify** the new directory as if it were a store, [below](#verifying). A failure keeps the directory, marks it
   `FAILED` with the reason, leaves `.comline/` as it was, and exits nonzero.
5. **Swap.** Set the journal `ready`. Rename `.comline/` to `.comline.format-N.bak/`. Rename `.comline.migrating/` to
   `.comline/`. Move `deps-cache/` from the backup into the new `.comline/`: offline machines depend on it, and today's
   wipe deletes it with everything else. Write the receipt and remove the journal.

Each rename is atomic. Between the two there is no `.comline/`, and that state is recognized and completed, not
mistaken for "never built".

### Crashes

The state is in the paths and the journal alone, so every step is resumable. Another command that finds an interrupted
migration stops and names `comline store migrate`, which resumes it; nothing resumes on its own.

| Interrupted | What is on disk | `comline store migrate` |
|---|---|---|
| steps 1 to 3 | `.comline/` intact, `.comline.migrating/` partial, journal `writing` | If the journal's old heads equal the store's, it resumes: writes are content-addressed, so repeating one writes the same bytes. Otherwise the store changed meanwhile: it stops and names the partial directory, which the user removes, or has `--restart` remove. |
| after verify, before the first rename | journal `ready` | completes step 5 |
| between the two renames | no `.comline/`, a backup and a ready directory | renames the ready directory into place |
| after both, before `deps-cache/` moved | new store in place, the cache in the backup | moves it |
| after | complete | nothing to do |

Running the whole command again on a migrated store is a no-op: the stamp is C. That is the idempotence of the
operation. The idempotence of the *function* is a [law](proof.md#laws).

### Verifying

Before the swap, on the new directory, every one of these is checked, and any failure stops the migration:

1. Every object decompresses, matches its hash, and every reference (tree entry, parent, `release.since`, ref)
   resolves.
2. Every version decodes under C, and encoding it again gives the same bytes: the encoding is canonical.
3. The old-to-new map is a bijection on commits, parents map to parents, and for each commit the `version`, `release`
   record, `author`, `timestamp` and `message` are the same as before.
4. The witness holds: `down` of every migrated version, through every step, equals the version as it was.
   Nothing a version recorded was lost. See [the witness](steps.md#the-witness).
5. The unknowns written are exactly the ones the chain declares. A step that wrote an undeclared one, or didn't write a
   declared one, fails here.
6. A payload whose bytes are the same in N and C kept its hash.

Reported, not failed: the `facts` of each version recomputed by the current core and compared with the carried
ones. A difference means a rule changed since the version was built, and is listed so that it isn't a surprise
later. The existing `compat` tests treat a recomputed history the same way.

## The backup

**Decided:** the old store is renamed to `.comline.format-N.bak/` beside the new one, and **kept until the user removes
it** with `comline store prune`, which removes a backup only when the store that replaced it passes `comline store
verify`. Nothing deletes one on its own, after a time or a number of builds. `comline store status` lists them.

It is a **sibling** and not a directory inside `.comline/`: `.comline/` is committed to Git, while a sibling shows in
`git status` as untracked, so it is visible and nobody commits it without choosing to. `comline new` can add it to the
`.gitignore` it already writes for `deps-cache/`; a migration never edits anyone's files. Objects the migration didn't
change are hard links, so a backup costs little.

## Reset

`comline store reset` is the only way a store with no path to the current format is replaced, and it is the user's
command:

- It renames `.comline/` to `.comline.format-N.bak/` and starts a new store at the next build. It deletes nothing, and
  `deps-cache/` is kept.
- On a terminal the user is asked to confirm **that exact action** (it names the store, the backup and the format), and
  nothing proceeds without it. Without a terminal it needs `--force`.
- No other command resets. `build` on such a store stops and names this one.

(`comline reset`, which deletes `.comline/` outright behind a typed confirmation, is today's command and unchanged.)

## Checking first

```text
comline store migrate --check
```

Does steps 1 to 2 and the in-memory part of the checks, and writes nothing: no `.comline.migrating/`, no lock. It prints
what would happen and exits with distinct codes for *nothing to do*, *would migrate* and *would be refused*, so it runs in CI
as a guard ("the checked-in store is current") and by hand before an upgrade.

```text
store format 3, 41 versions (0.1.0-dev.1 … 0.9.0)
  would migrate 3 -> 4: 41 versions, 118 objects rewritten, 1,204 unchanged
  unknown after migration: 52 (chains: 52)
    0.7.0  protocols/Billing/given_up/bounded_size/chain      format 3 records the set, not the path to its cause
    …
  nothing deleted: the old store is kept as .comline.format-3.bak
```

(An illustration of the content, not a format.)

## The CLI

Only the touchpoints are named here.

| Command | Does |
|---|---|
| `comline store status` | The stamp, the versions, whether a migration is needed, the unknowns per version, the backups there are. |
| `comline store migrate [--check] [--assume-format N] [--map FILE]` | The procedure above. `--map` writes the old-to-new hashes, for anything outside the store that recorded one. |
| `comline store verify` | The [checks](#verifying) on the current store. Also what `core#182` asks for: a damaged store says which file, and what to do. |
| `comline store prune` | Removes verified backups, when the user runs it. |
| `comline store reset` | [Moves a store with no path aside](#reset), on the user's confirmation. |
| `comline store replay` | *Proposed:* [rebuild from Git](steps.md#what-cannot-be-migrated). |
| `comline build`, `comline release` | **Stop** when the store is older, and name `comline store migrate` or `reset`; on a terminal they ask whether to run the migration, and do nothing without a yes. They never change a store on their own. |

There is no flag or variable that makes a command migrate or reset by itself: a machine that must migrate runs
`comline store migrate`.

## Git

`.comline/` is committed, so a migration is a change in a repository, and two people can make it. Migrating is
deterministic: a step is a pure function and the engine hashes bottom-up, so migrating the same old commit gives the
same new hashes in every clone. Two developers who migrate separately produce the same files, and Git merges them
without a conflict. This is why the receipt (`.comline/MIGRATIONS`, one line per migration) holds no time, no author and
no core version: the same on every machine, so it never conflicts either. New hashes are new files, so the only files
two sides can conflict on are `FORMAT_VERSION` and `refs/heads/main`.

**Decided:** a Git merge of stores in two formats is **refused.** A command that finds a conflicted stamp whose sides
are different formats stops with "migrate both sides first": check out each branch, run `comline store migrate`, then
merge. Because migration converges, the merge is then the ordinary one, and the ordinary
[reconcile](../../guides/ir/cas.md#branches) joins the heads, as it does today. Nothing is resolved on the user's
behalf.
