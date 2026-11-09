# Supplying dependencies and tooling

Status: **draft** · part of [Offline and air-gapped use](index.md)

**The question.** How do dependencies, and Comline itself, get onto a machine
or into a network that can't fetch them, without that ever changing what is
built?

## Identity is the hash, location is replaceable

A dependency is identified by its pin: a version or a commit, and its content
hash. *Where* the bytes come from is a separate, replaceable thing. Every
route below is just another place to find the same hash-checked content, so
none can change a build: at worst one can fail to supply it.

## Several sources per dependency

A dependency may list several sources, in order, so it stays available
whatever happens to one of them:

```text
billing = {
    version = "1.4.0"
    hash = "blake3:…"
    sources = [
        { registry = "comline" }
        { registry = "https://registry.acme.internal" }
        { git = "https://github.com/acme/billing", commit = "…" }
    ]
}
```

- **More than one source requires a hash.** A registry download and a git
  checkout of the same package give the same content hash, and nothing else
  they carry (a version string, a commit) says anything about the other.
- **An unreachable source, or one without the content, falls through** to the
  next.
- **A source serving the wrong content is a hard error** naming it. Moving on
  would still build the right bytes, but would hide what may be a
  compromised source.

### Who can add sources

- **The package**, in its `config.idp`.
- **Machine or organisation configuration:** mirrors, as URL prefix rewrites
  (`https://github.com/` → `https://git.acme.internal/`) or sources put ahead
  of a package's own, without editing any package. Safe because the hash
  decides.
- **The root package, for a transitive dependency,** when that dependency's
  pin carries a hash: if C's only source is unreachable from your network and
  the pin is in B's config, the root adds a source for C. It **adds, never
  replaces**: content other than what B pinned would change what is built,
  and possibly C's given-up guarantees. Replacing (a patch) is out of scope.

### Order

Machine and organisation mirrors first, then the root's additions, then the
package's own sources. Mirrors first keeps lookups inside the organisation:
each source tried learns the dependency's name. Offline, only local sources
count: the vendored copy, the cache, bundles.

The build reports which source served each dependency (verbose output and
`--json`). That's never frozen: location isn't identity.

## The shared cache

One content-addressed cache per machine, keyed by hash, in place of today's
per-package `.comline/deps-cache/`. Every route below feeds it, and a build
reads from it. Projects on the same machine share what's been fetched, and a
copy is checked against its hash on the way in.

## Vendoring

`comline vendor` writes every dependency a package needs, transitive ones
included, into a directory in the project, each with its pin and hash. It
travels with the repository through any channel that carries it, and a
change to a dependency shows up as a diff in review. A build uses a vendored
copy only when it matches its pin.

## Mirrors

An internal git server or registry mirror, set once per machine or
organisation, as above. Suited to organisations with many projects; a future
registry needs the same mechanism.

## Bundles

A single signed archive of dependencies, carried across the gap and imported
into the cache on the other side: `comline bundle export` on a connected
machine, `comline bundle import` on the sealed one. Each entry is checked
against its hash on import, and the archive's signature against a key the
sealed side trusts. The same format can carry the tooling.

## Generated code's dependencies

Generated Rust depends on `comline-runtime` by a git rev, and generated
TypeScript on `@comline/runtime` from npm. Each ecosystem has its own offline
tools (`cargo vendor`, registry mirrors, npm caches), which work best with
published packages.

- **Publishing the runtimes to crates.io and npm is a hard requirement for
  1.0.** Generated code then names a version, not a git rev.
- **Until then**, the docs say how to vendor them for a sealed build:
  `cargo vendor` handles git dependencies, and `npm pack` produces a tarball
  to install from.

## Tooling into the gap

- **Release artifacts:** the CLI and the language server prebuilt for each
  platform, with checksums and signatures, rather than `cargo install` from
  source only.
- **Reproducible builds:** anyone can rebuild an artifact from source and
  compare bytes, as comline-typescript already does for its wasm core.
- **An SBOM per release**, for sealed environments' audits.
- **An offline docs bundle:** the documentation as a self-contained archive,
  with no outside assets (no Google Fonts), and generated schema docs
  (`doc-html`) likewise.

## Open questions

- The cache's location on each OS, and how it's cleaned.
- The mirror configuration format.
- The bundle format, and how its signing keys are distributed and trusted.
- The release signing scheme (sigstore, minisign, ...).
- The SBOM format (SPDX or CycloneDX).
