#!/usr/bin/env bash
set -euo pipefail

fail() { printf 'Ruleset sync: %s\n' "$*" >&2; exit 1; }
[[ -n "${GH_TOKEN:-}" ]] || fail 'GH_TOKEN secret is required.'
[[ "${RELEASE_APP_ID:-}" =~ ^[1-9][0-9]*$ ]] || fail 'RELEASE_APP_ID must be a positive GitHub App ID.'
[[ "${GITHUB_REPOSITORY:-}" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]] || fail 'Invalid repository identifier.'
api() { gh api -H 'Accept: application/vnd.github+json' -H 'X-GitHub-Api-Version: 2026-03-10' "$@"; }
repo="repos/$GITHUB_REPOSITORY"
permission=$(api "$repo") || fail 'Cannot read repository permissions.'
jq -e '.permissions.admin == true' <<<"$permission" >/dev/null || fail 'The GH_TOKEN identity must have repository administrator permission.'
temporary=$(mktemp -d)
trap 'rm -rf "$temporary"' EXIT
# Validate every configuration before the first remote mutation.
for file in .github/rulesets/*.json; do
  jq -e '(.name | type == "string") and (.target == "tag" or .target == "branch") and .enforcement == "active" and (.rules | type == "array")' "$file" >/dev/null || fail "Invalid ruleset: $file"
  jq --argjson app "$RELEASE_APP_ID" '(.bypass_actors[] | select(.actor_type == "Integration" and .actor_id == 0) | .actor_id) = $app' "$file" > "$temporary/$(basename "$file")" || fail "Cannot prepare $file"
done
existing=$(api --paginate --slurp "$repo/rulesets?includes_parents=false&per_page=100") || fail 'Cannot list repository rulesets.'
existing=$(jq 'add' <<<"$existing")
for file in "$temporary"/*.json; do
  name=$(jq -r '.name' "$file")
  matches=$(jq --arg name "$name" '[.[] | select(.name == $name)]' <<<"$existing")
  count=$(jq 'length' <<<"$matches")
  [[ "$count" -le 1 ]] || fail "Multiple rulesets named $name; resolve ambiguity manually."
  if [[ "$count" == 1 ]]; then
    id=$(jq -r '.[0].id' <<<"$matches")
    api --method PUT "$repo/rulesets/$id" --input "$file" >/dev/null || fail "Failed to update $name"
  else
    api --method POST "$repo/rulesets" --input "$file" >/dev/null || fail "Failed to create $name"
  fi
  printf 'Synchronized: %s\n' "$name"
done
# Retire only this exact name, only after both desired rulesets succeeded.
while IFS= read -r id; do
  [[ -n "$id" ]] || continue
  api --method DELETE "$repo/rulesets/$id" >/dev/null || fail "Failed to delete retired ruleset $id"
done < <(jq -r '.[] | select(.name == "Restrict default branch updates administrators") | .id' <<<"$existing")
