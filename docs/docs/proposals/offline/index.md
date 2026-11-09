# Offline and air-gapped use

Status: **draft** · two parts, read in order:
[fetching](fetching.md), then [supplying dependencies and tooling](supply.md)

**The question.** Nothing yet says how Comline works without internet
access. **What must hold, in every repository, so Comline can be used on a
machine or in a network that can't reach the internet, and so a build there
is exactly the build anywhere else?**

## The situations

All four are in scope:

| Situation | What it needs |
|---|---|
| **An offline developer machine** | Work from what was fetched earlier, or from a bundle, and be told clearly what's missing. |
| **An isolated build or CI network** | Build and generate from vendored copies or internal mirrors, never reaching outside. |
| **An air-gapped deployment** | Services built with Comline run in a sealed network: the runtime and generated code need nothing beyond the peer they talk to. |
| **The tooling into the gap** | The CLI, the language server, generators and docs brought into a sealed network, verifiably. |

## What it looks like today

| Part | Network today | Already offline-friendly |
|---|---|---|
| **core** (dependencies) | A `Git` dependency is fetched by the system `git` into a per-package `.comline/deps-cache/`. `Registry` sources exist in the config (with `hash` and `signature`) but nothing resolves them. | Pins are exact commits, and a checkout is reused. A mode that never fetches exists, which the language server uses. A declared `hash` (blake3 of the dependency's compiled content) is checked; without one, core warns and trusts the fetch. |
| **cli** | `check`, `add` and `build` fetch through core. It installs only with `cargo install --path .`: no release binaries, checksums or signatures. | Generators are built in, or local executables and `.wasm` files: nothing is downloaded. |
| **language server** | None. | It never fetches, and says "isn't fetched yet — run `comline check`". |
| **generated code** | Rust depends on `comline-runtime` by a git rev; TypeScript on `@comline/runtime` from npm. | Otherwise self-contained. |
| **runtime** | None beyond the peer it's given. | Fits air-gapped deployment as it is. |
| **specification** | The vendoring scripts clone from GitHub, only when a developer runs them. | Copies are committed, pinned and checked. |
| **docs** | The theme loads Google Fonts by default. | — |

Nothing reports usage or checks for updates.

## Rules that hold whatever the details

- **Choosing is separate from getting.** Choosing a dependency (`add`, a
  future `update`) writes pins, and uses the network only when the user asks.
  Getting bytes that are already pinned follows [the fetching
  rules](fetching.md).
- **Identity is the hash, location is replaceable.** Where bytes come from
  (a registry, git, a mirror, a vendored copy, a cache, a bundle) never
  changes what is built. A copy is accepted only when it matches the pin.
- **Offline is absolute.** When the environment says offline, nothing touches
  the network, whatever any package says.
- **Nothing calls home.** The runtime and generated code never reach anything
  but the peer they're given. No tool sends telemetry or checks for updates.
  The language server never fetches.

## Rollout

In stages, each useful on its own:

1. **Fetching rules in core and the CLI:** the offline switch, `comline
   fetch`, the package settings and their precedence, and the hash rules.
2. **The shared cache and vendoring:** one hash-keyed cache per machine, in
   place of the per-package deps cache, and `comline vendor`.
3. **Several sources per dependency, and mirrors:** ordered sources, machine
   and organisation mirrors, and the root package's additions.
4. **Bundles:** export and import of a signed archive.
5. **Tooling into the gap:** release artifacts with checksums, signatures and
   an SBOM, reproducible builds, and an offline docs bundle.
6. **Generated code's dependencies:** the runtimes published to crates.io and
   npm, a hard requirement for 1.0. Until then, the docs say how to vendor
   them.

## Open questions

Collected from both parts:

- The names of the settings, and where machine and organisation config live.
- The cache's location on each OS.
- The mirror configuration format.
- The bundle format and its signing keys.
- The release signing scheme (sigstore, minisign, ...).
- The SBOM format (SPDX or CycloneDX).
