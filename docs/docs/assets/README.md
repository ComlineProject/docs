# Vendored brand assets

Copied from the `ComlineProject/brand` repo — do not edit here.

| File | Source | Taken from commit | Used for |
|---|---|---|---|
| `comline-mark.svg` | `logo/mark-tomato.svg` | `17ea20a` | `theme.logo` base / fallback |
| `comline-mark-light.svg` | `logo/mark-tomato.svg` | `17ea20a` | light (`default`) scheme header |
| `comline-mark-dark.svg` | `logo/mark-cream.svg` | `17ea20a` | dark (`slate`) scheme header |
| `favicon.svg` | `favicon/favicon.svg` | `17ea20a` | `theme.favicon` |

The per-scheme header swap is done in `stylesheets/nav.css` (`content: url(...)`
under `[data-md-color-scheme=...]`).

To update: change the file in the brand repo, then re-copy and bump the
commit above.
