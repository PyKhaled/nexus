#!/usr/bin/env bash
# Add a repository/submodule declaration. MUTATES blueprint and Git state.
set -Eeuo pipefail

usage() {
  cat <<'USAGE'
Usage:
  repository_add.sh BLUEPRINT NAME URL [options]

Options:
  --path PATH       Repository path (default: system/NAME)
  --branch BRANCH   Track/add a specific branch
  --optional        Mark repository as optional (required: false)
  --root ROOT       Project/Git root (default: blueprint directory)
  -h, --help        Show this help

Dependencies: git, yq (mikefarah/yq v4+), jq
USAGE
}

fail() { printf 'error: %s\n' "$*" >&2; exit 1; }
need() { command -v "$1" >/dev/null 2>&1 || fail "required command not found: $1"; }

[[ $# -ge 1 ]] || { usage >&2; exit 2; }
[[ ${1:-} != -h && ${1:-} != --help ]] || { usage; exit 0; }
[[ $# -ge 3 ]] || { usage >&2; exit 2; }

blueprint=$1
name=$2
url=$3
shift 3

repo_path=""
branch=""
required=true
root=""

while (($#)); do
  case "$1" in
    --path)
      (($# >= 2)) || fail "--path requires a value"
      repo_path=$2; shift 2 ;;
    --branch)
      (($# >= 2)) || fail "--branch requires a value"
      branch=$2; shift 2 ;;
    --optional)
      required=false; shift ;;
    --root)
      (($# >= 2)) || fail "--root requires a value"
      root=$2; shift 2 ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      fail "unknown argument: $1" ;;
  esac
done

need git
need yq
need jq

[[ -f "$blueprint" ]] || fail "blueprint not found: $blueprint"
[[ $name =~ ^[a-z][a-z0-9-]{0,62}$ ]] || fail "invalid repository name: $name"

[[ -n $repo_path ]] || repo_path="system/$name"
case "$repo_path" in
  system/*) ;;
  *) fail "repository path must remain under system/: $repo_path" ;;
esac

# Reject absolute paths and traversal.
[[ $repo_path != /* ]] || fail "repository path must be relative: $repo_path"
IFS='/' read -r -a _parts <<< "$repo_path"
for _part in "${_parts[@]}"; do
  [[ $_part != ".." ]] || fail "repository path may not contain '..': $repo_path"
done

if [[ -z $root ]]; then
  root=$(cd "$(dirname "$blueprint")" && pwd)
else
  root=$(cd "$root" && pwd)
fi

blueprint=$(cd "$(dirname "$blueprint")" && pwd)/$(basename "$blueprint")

git -C "$root" rev-parse --show-toplevel >/dev/null 2>&1 || fail "root is not inside a Git repository: $root"

# Ensure a repositories list exists and prevent duplicates by name/path.
existing_name=$(yq -r --arg name "$name" '.repositories // [] | map(select(.name == $name)) | length' "$blueprint")
(( existing_name == 0 )) || fail "repository name already declared: $name"

existing_path=$(yq -r --arg path "$repo_path" '.repositories // [] | map(select(.path == $path)) | length' "$blueprint")
(( existing_path == 0 )) || fail "repository path already declared: $repo_path"

abs_repo="$root/$repo_path"
[[ ! -e "$abs_repo" ]] || fail "destination already exists: $abs_repo"

mkdir -p "$(dirname "$abs_repo")"

# Mutate Git state first. If blueprint mutation fails, attempt to roll back the submodule.
git_args=(submodule add)
[[ -n $branch ]] && git_args+=( -b "$branch" )
git_args+=( "$url" "$repo_path" )

git -C "$root" "${git_args[@]}"

rollback() {
  git -C "$root" submodule deinit -f -- "$repo_path" >/dev/null 2>&1 || true
  git -C "$root" rm -f --cached "$repo_path" >/dev/null 2>&1 || true
  rm -rf -- "$abs_repo" "$root/.git/modules/$repo_path" >/dev/null 2>&1 || true
}

export NEXUS_REPO_NAME="$name"
export NEXUS_REPO_URL="$url"
export NEXUS_REPO_PATH="$repo_path"
export NEXUS_REPO_BRANCH="$branch"
export NEXUS_REPO_REQUIRED="$required"

if ! yq -i '
  .repositories = (.repositories // []) |
  .repositories += [{
    "name": strenv(NEXUS_REPO_NAME),
    "url": strenv(NEXUS_REPO_URL),
    "path": strenv(NEXUS_REPO_PATH),
    "required": (strenv(NEXUS_REPO_REQUIRED) == "true")
  }] |
  if strenv(NEXUS_REPO_BRANCH) != "" then
    .repositories[-1].branch = strenv(NEXUS_REPO_BRANCH)
  else . end
' "$blueprint"; then
  rollback
  fail "failed to update blueprint; Git submodule changes were rolled back where possible"
fi

jq -n \
  --arg blueprint "$blueprint" \
  --arg name "$name" \
  --arg url "$url" \
  --arg path "$repo_path" \
  --arg branch "$branch" \
  --argjson required "$required" \
  '{
    action: "added",
    blueprint: $blueprint,
    repository: {
      name: $name,
      url: $url,
      path: $path,
      required: $required
    }
  } | if $branch != "" then .repository.branch = $branch else . end'
