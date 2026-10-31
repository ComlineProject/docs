#!/usr/bin/env bash
# Apply labels.yml to every non-archived ComlineProject repository.
#
#   scripts/sync-labels.sh            create or update every label
#   scripts/sync-labels.sh --prune    also delete labels not in labels.yml
#
# Needs gh (logged in, with repo scope) and python3 with PyYAML.
# Without --prune it never deletes anything.
set -euo pipefail

ORG=ComlineProject
here="$(cd "$(dirname "$0")/.." && pwd)"
prune=0
[ "${1:-}" = "--prune" ] && prune=1

# One tab-separated line per label: name, color, description.
labels="$(python3 - "$here/labels.yml" <<'PY'
import sys, yaml
for l in yaml.safe_load(open(sys.argv[1])):
    print("\t".join([l["name"], l["color"], l["description"]]))
PY
)"

repos="$(gh repo list "$ORG" --limit 200 --no-archived --json name -q '.[].name')"

for repo in $repos; do
  echo "== $ORG/$repo"
  while IFS=$'\t' read -r name color desc; do
    gh label create "$name" --repo "$ORG/$repo" --color "$color" \
      --description "$desc" --force >/dev/null
  done <<<"$labels"

  if [ "$prune" = 1 ]; then
    wanted="$(cut -f1 <<<"$labels")"
    gh label list --repo "$ORG/$repo" --limit 200 --json name -q '.[].name' |
      while IFS= read -r have; do
        if ! grep -qxF -- "$have" <<<"$wanted"; then
          echo "   prune: $have"
          gh label delete "$have" --repo "$ORG/$repo" --yes
        fi
      done
  fi
done
