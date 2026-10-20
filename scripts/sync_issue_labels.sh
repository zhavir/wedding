#!/usr/bin/env bash
set -euo pipefail
jq -e 'type == "array" and all(.[]; (.name | type == "string") and (.color | test("^[0-9a-fA-F]{6}$")) and (.description | type == "string"))' .github/issue-labels.json >/dev/null || { echo 'Invalid issue-labels.json.' >&2; exit 1; }
[[ -n "${GH_TOKEN:-}" ]] || { echo 'GH_TOKEN is required.' >&2; exit 1; }
[[ "${GITHUB_REPOSITORY:-}" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]] || { echo 'Invalid repository identifier.' >&2; exit 1; }
while IFS= read -r label; do
  name=$(jq -r '.name' <<<"$label")
  color=$(jq -r '.color' <<<"$label")
  description=$(jq -r '.description' <<<"$label")
  gh label create "$name" --repo "$GITHUB_REPOSITORY" --color "$color" --description "$description" --force || { printf 'Failed to synchronize label: %s\n' "$name" >&2; exit 1; }
done < <(jq -c '.[]' .github/issue-labels.json)
