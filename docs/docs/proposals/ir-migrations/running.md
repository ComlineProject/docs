# Running a migration

Status: **draft** · part of [Migrating stored IR across format versions](index.md)

**The question.** How does a store change format without any moment at which history is lost, however the process
ends, and how does someone find out what it would do first?

## What each command does with each stamp

`ensure_compatible_store` stops deleting. With the stamp *N* and a binary that writes *C*:

| The store | A read command (`diff`, `doc`, `generate`, `inspect`) | A write command (`build`, `release`) |
|---|---|---|
| N = C | proceeds | proceeds |
| N < C, and N is supported | reads through an **in-memory** migration and writes nothing | migrates, then proceeds |
| N < C, N unsupported, or unstamped | an error that names the format and the [options](steps.md#what-cannot-be-migrated) | the same error |
| **N > C** | an error: the store is format N, this comline reads up to C, and *comline ≥ X* reads N | the same error; nothing written |
| a stamp that isn't a number, or has conflict markers on one side | an error naming the file ([see Git](#git)) | the same |

Reading an old store needs no write because a migration is a pure function: a read command can run the chain on the
versions it needs and drop the result. That makes `comline diff`, `doc --version` and `generate` work on a store nobody
has migrated yet, at the cost of the memory and time of the chain, which a cache can hide.

Two of today's behaviors go: deleting an older store, and deleting a newer one. The second is the more dangerous.
`stored != Some(CURRENT)` is true for a store that is ahead of the binary.

## The procedure

`comline store migrate`, and the same code behind `build` and `release`:

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

The state is in the paths and the journal alone, so every step is resumable by the next run of any command that opens
the store:

| Interrupted | What is on disk | The next run |
|---|---|---|
| steps 1 to 3 | `.comline/` intact, `.comline.migrating/` partial, journal `writing` | If the journal's old heads equal the store's, it resumes: writes are content-addressed, so repeating one writes the same bytes. Otherwise the store changed meanwhile, so the partial directory is deleted and it starts again. |
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

The old store is renamed to `.comline.format-N.bak/` beside the new one. **Kept until someone removes it:**
`comline store prune` removes backups, and only when the store that replaced them passes `comline store verify`.
Nothing deletes one on its own, after a time or after a number of builds, and `build` mentions it once.

It is a **sibling** and not a directory inside `.comline/` for two reasons. The shipped binaries delete `.comline/`
on a stamp they don't expect, so a backup inside would go with it. And `.comline/` is committed to Git while a sibling
shows in `git status` as untracked, so it is visible and nobody commits it without choosing to. `comline new` can add
it to the `.gitignore` it already writes for `deps-cache/`; the migration itself does not edit anyone's files.

*Open:* the name and place, and whether disk use warrants a default expiry. Leaning: no expiry. A store is small,
objects the migration didn't change are hard links, and the backup is the only copy of the old format.

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
| `comline store prune` | Removes verified backups. |
| `comline store replay` | *Proposed:* [rebuild from Git](steps.md#what-cannot-be-migrated). |
| `comline build`, `comline release` | Migrate first when the store is older, and say so. |

`build` deleted the store without asking; migrating it without asking is strictly safer, and the plan is printed. *Open:*
whether the default should instead be to stop and ask. A store is committed to Git, so a migration is a large diff the
author didn't write, which is an argument for asking once. `--no-migrate`, or `COMLINE_STORE_MIGRATE=never`, makes an
old store an error for the machine that must not write.

## Git

`.comline/` is committed, so a migration is a change in a repository, and two people can make it. Three properties make
that safe, and one is open.

- **Convergence.** A step is deterministic and the engine hashes bottom-up, so migrating the same old commit gives the
  same new hashes in every clone. Two developers who migrate separately produce the same files, and Git merges them
  without a conflict. This is why the receipt (`.comline/MIGRATIONS`, one line per migration) holds no time, no
  author and no core version: the same on every machine, so it never conflicts either.
- **The objects merge by name.** New hashes are new files. The only files two sides can conflict on are
  `FORMAT_VERSION` and `refs/heads/main`.
- **A branch that didn't migrate** brings old-format objects and its own head. `store migrate` accepts a conflicted
  stamp whose sides are both supported formats and a conflicted ref (`Heads::Two`), migrates the older side's chain,
  which yields the same objects the other side already has for the commits they share, and leaves the ordinary
  [reconcile](../../guides/ir/cas.md#branches) to join the heads, as it does today.

*Open:* the conflicted stamp is parsed by hand, and what a developer sees when the two sides disagree is a conflict in
a one-line file. The error needs to say what to do. Whether the engine should resolve it itself is not settled.

### Older binaries

A binary that predates this proposal deletes any store whose stamp isn't its own, a newer one included. Nothing in
the store can stop that, so the order of releases does:

1. The pull request that makes a newer store an error ships in a **release first**, and the docs and the CLI say that
   every machine that touches a repository has to have it before format 4 lands.
2. Even then, a binary older than the release deletes a format-4 store. Git has the history, and the backup, being a
   sibling, survives it.

*Open:* the stronger fix is to put the format-4 store somewhere an older binary doesn't look, such as `.comline/` for
format 3 and a new directory name for 4. An older binary then finds no store and starts a new one without touching the
new. It costs a rename across the docs, the CLI, the language server's exclusion list and `.gitignore`. It might be the
price of making this once and for all safe, and it can only be done at a format boundary.
