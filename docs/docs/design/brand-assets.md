# Brand assets

Status: **In use** — `ComlineProject/brand` holds the canonical files; the docs
site vendors the mark and favicon from it. Other consumers still carry their own
copies · Affects `ComlineProject/brand`, `ComlineProject/docs`,
`ComlineProject/package-registry-frontend`, `ComlineProject/shared-web`,
`ComlineProject/comline`

## The problem

The Comline mark and its colours currently live only in the package-registry
frontend's `static/` folder, where they were first drawn. Every other surface
that needs the logo — the docs site, the landing page, the
[playground and tutorial](playground-and-tutorial.md), READMEs — either has no
mark or has a stale hand-copied one. There is no place that is *the* mark, and no
record of which shade of red is correct.

## Decision

**`ComlineProject/brand` is the single source of truth.** It holds the mark in
its colour variants, the favicons, the third-party marks we place next to ours
(GitHub, GitLab), and a `tokens.json` of the brand colours. Changes are made
there first.

**Consumers vendor a pinned copy.** Each repo that renders the mark copies the
file it needs into its own tree and records the `brand` commit it came from. No
repo hotlinks `brand` at build or run time — a raw-GitHub URL is not a CDN, and a
submodule would couple every consumer's checkout to it. The files are a few KB of
SVG that change a handful of times a year; a copy with a provenance note is the
right weight.

## Layout of `brand`

```
logo/
  mark.svg          fill="currentColor" — follows the surrounding text colour
  mark-tomato.svg   #E5442E — the mark on a light surface
  mark-cream.svg    #FFE1D8 — the mark on a tomato / dark surface
favicon/
  favicon.svg       cream mark on a tomato rounded-square — browser tabs
  favicon.png       raster fallback
third-party/
  github-mark-dark.svg / github-mark-light.svg
  gitlab-mark.svg
tokens.json         { "color": { "tomato": "#E5442E", "cream": "#FFE1D8" } }
README.md           which file where, the don'ts, per-consumer update paths
```

The mark itself: a 4×4 grid of rounded squares on a `0 0 100 100` viewBox with
one row left as negative space. It carries `role="img"` and
`aria-label="Comline"` so it announces correctly on its own; a consumer that
places it directly beside the word "Comline" should set `aria-hidden="true"`
instead.

### Colours

| Token | Hex | Use |
|---|---|---|
| tomato | `#E5442E` | primary — logo on light, favicon background, accents |
| cream | `#FFE1D8` | the mark on tomato / dark, favicon foreground |

## The sync pattern

1. Change the file in `brand`, commit, push.
2. In each consumer that renders it, re-copy the file and bump the recorded
   commit. For the docs site that record is
   [`docs/docs/assets/README.md`](https://github.com/ComlineProject/docs/blob/main/docs/docs/assets/README.md).
3. Consumers pick up the change on their next deploy — there is no automatic
   propagation, by design.

### Known consumers

| Repo | Vendored copy lives in | Rendered as |
|---|---|---|
| `docs` | `docs/docs/assets/` | `mkdocs.yml` `theme.logo` / `theme.favicon` |
| `package-registry-frontend` | `static/images/comline/`, `static/favicon.*` | header bar, `app.html` |
| `shared-web` | per its own convention | shared web components |
| `comline` (landing) | `static/` | header, hero |

## Follow-ups

- **Docs palette.** The site still uses Material's stock `teal` primary. Moving
  `palette.primary` to a custom tomato (`--md-primary-fg-color: #E5442E`) would
  put the header on-brand; it needs a contrast check against the header text and
  the two colour schemes before it lands.
- **`shared-web` as the web consumers' relay.** If the playground, tutorial, and
  landing site end up sharing a component layer (`shared-web`), that layer — not
  each app — should carry the one vendored copy.
- **`tokens.json` → build input.** Nothing consumes `tokens.json` yet. A web
  build could generate a CSS custom-property file from it so the colours are
  never retyped.
- **Publishing `brand`.** The repo exists locally; it needs to be created under
  the `ComlineProject` org and pushed (`git push -u origin main` — the remote is
  already set).
