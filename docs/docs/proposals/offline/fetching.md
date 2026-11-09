# Fetching

Status: **draft** · part of [Offline and air-gapped use](index.md)

**The question.** When may a Comline tool use the network, who decides, and
what must a fetched copy prove before it's used?

## Choosing and getting

Two different acts, which today are mixed:

- **Choosing** what a package depends on: `comline add`, and a future
  `comline update`. It writes pins (a commit, a version, a hash) into
  `config.idp`, and is the only act that may look for something new. It uses
  the network only because the user asked.
- **Getting** the bytes a pin already names. The pin decides what they are;
  the network only decides whether they're here yet.

Everything below is about getting.

## The default: on demand, with a hard switch

A build (`check`, `build`, `generate`, ...) fetches any pinned content it
doesn't have yet, as today.

- **`comline fetch`** fetches ahead of time exactly what a build would fetch,
  and nothing else: the step to run before a machine goes offline, or in a CI
  stage that's allowed out.
- **The offline switch** forbids all network access: `--offline` on any
  command, an environment variable, or machine configuration. A build that
  is missing something then fails with one error listing *everything*
  missing, not the first thing it tripped on, and saying how to supply it
  (`comline fetch` elsewhere, a vendored copy, a bundle).
- **The language server never fetches**, offline or not. It shows a missing
  dependency the way `check` would describe it.

## Package settings

A package can tighten this in `config.idp`, for when its situation needs it:
a package built for a sealed customer, say, should behave strictly on every
developer's machine and in every CI, not only on the machines set up for it.

- **Explicit fetching:** a build never fetches; only `comline fetch` does.
  Builds stay offline by construction, at the cost of one step after a clone
  or a pin change.
- **Required hashes:** every non-path dependency must declare its hash (see
  below).

## Precedence: the strictest wins

The environment (the switch, machine and organisation configuration) and the
**root** package's settings combine, and the strictest applies:

- **Offline is absolute.** No package setting can allow the network back.
- **A package only tightens.** Its settings can make a build stricter than the
  environment, never looser.
- **A dependency's settings apply to its own builds only.** Otherwise a
  dependency could make every consumer's build stricter, or looser, without
  them knowing.

| Environment | Root package | A build may fetch | Hash required (git) |
|---|---|---|---|
| online | default | yes, pinned content only | no (warning) |
| online | explicit fetching | no; `comline fetch` may | no (warning) |
| online | required hashes | yes | yes |
| offline | anything | no | yes |

## Hashes

A dependency's `hash` is the blake3 of its compiled content, and core already
checks a declared one. When it's **mandatory**:

- **A registry dependency: always.** A version string can be republished with
  other content, so without a hash the pin names nothing.
- **A git dependency: when offline, or when the root package requires hashes.**
  Otherwise the pinned commit already identifies the content, and today's
  warning stays.
- **Any dependency with more than one source** ([supply](supply.md#several-sources-per-dependency)):
  the sources don't share any other identity.

Offline is when the hash matters most: the bytes then come from a vendored
copy, a cache or a carried bundle, which have passed through other hands, and
the hash is what proves a copy is the pinned content.

A copy whose hash doesn't match is **an error, never a fallback**, naming
where it came from: it may be compromised.

## Options considered

| | On demand + switch (proposed) | Explicit fetch only |
|---|---|---|
| Day to day | as today | one more step after a clone or a pin change |
| A sealed environment | safe once the switch is set | safe by default |
| Strictness for one package | the package's "explicit fetching" setting | always |

On-demand with a switch keeps everyday use as it is; a mandatory hash where
it matters means getting can't change what is built; and a package that
needs the stricter behaviour asks for it, so it holds wherever the package is
built.

## Open questions

- The setting names, and where machine and organisation configuration live.
- Whether `comline fetch` also takes `--for <target>` to fetch only what one
  target's generation needs.
