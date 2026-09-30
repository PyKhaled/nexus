#!/usr/bin/env bash
# Synchronize declared repositories. MUTATES Git/submodule state.
set -Eeuo pipefail

usage() {
  cat <<'USAGE'
Usage:
  repository_sync.sh BLUEPRINT [--root ROOT]

Options:
  --root ROOT       Project/Git root (default: blueprint directory)
  -h, --help        Show this help

Dependencies: git, yq, jq
USAGE
}

fail() { printf 'error: %s\n' "$*" >&2; exit 1; }
need() { command -v "$1" >/dev/null 2>&1 || fail "required command not found: $1"; }

[[ $# -ge 1 ]] || { usage >&2; exit 2; }
[[ ${1:-} != -h && ${1:-} != --help ]] || { usage; exit 0; }

blueprint=$1
shift
root=""

while (($#)); do
  case "$1" in
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

if [[ -z $root ]]; then
  root=$(cd "$(dirname "$blueprint")" && pwd)
else
  root=$(cd "$root" && pwd)
fi
blueprint=$(cd "$(dirname "$blueprint")" && pwd)/$(basename "$blueprint")

git -C "$root" rev-parse --show-toplevel >/dev/null 2>&1 || fail "root is not inside a Git repository: $root"

count=$(yq -r '.repositories // [] | length' "$blueprint")
results='[]'
required_failures=0

for ((i=0; i<count; i++)); do
  name=$(yq -r ".repositories[$i].name // \"\"" "$blueprint")
  url=$(yq -r ".repositories[$i].url // \"\"" "$blueprint")
  repo_path=$(yq -r ".repositories[$i].path // \"\"" "$blueprint")
  branch=$(yq -r ".repositories[$i].branch // \"\"" "$blueprint")
  required=$(yq -r ".repositories[$i].required // true" "$blueprint")

  status="synced"
  message=""

  if [[ ! $name =~ ^[a-z][a-z0-9-]{0,62}$ ]]; then
    status="error"; message="invalid repository name"
  elif [[ $repo_path != system/* || $repo_path == /* || $repo_path == *'/../'* || $repo_path == ../* || $repo_path == */.. ]]; then
    status="error"; message="repository path must remain under system/"
  elif [[ -z $url ]]; then
    status="error"; message="repository URL is missing"
  else
    # Keep .gitmodules metadata aligned with declared URL/branch when the submodule exists.
    if git -C "$root" config -f .gitmodules --get-regexp '^submodule\..*\.path$' 2>/dev/null | awk '{print $2}' | grep -Fxq "$repo_path"; then
      submodule_name=$(git -C "$root" config -f .gitmodules --get-regexp '^submodule\..*\.path$' | awk -v p="$repo_path" '$2==p {k=$1; sub(/^submodule\./,"",k); sub(/\.path$/,"",k); print k; exit}')
      git -C "$root" config -f .gitmodules "submodule.${submodule_name}.url" "$url"
      if [[ -n $branch ]]; then
        git -C "$root" config -f .gitmodules "submodule.${submodule_name}.branch" "$branch"
      fi
    fi

    if ! sync_output=$(git -C "$root" submodule sync -- "$repo_path" 2>&1); then
      status="error"; message="$sync_output"
    elif ! update_output=$(git -C "$root" submodule update --init --recursive -- "$repo_path" 2>&1); then
      status="error"; message="$update_output"
    elif [[ -n $branch ]]; then
      # For declared tracking branches, move the submodule to the latest remote branch tip.
      if ! branch_output=$(git -C "$root" submodule update --remote --recursive -- "$repo_path" 2>&1); then
        status="error"; message="$branch_output"
      fi
    fi
  fi

  if [[ $status == error && $required == true ]]; then
    required_failures=$((required_failures + 1))
  fi

  item=$(jq -n \
    --arg name "$name" \
    --arg path "$repo_path" \
    --arg status "$status" \
    --arg message "$message" \
    --argjson required "$required" \
    '{name:$name,path:$path,required:$required,status:$status} + (if $message != "" then {message:$message} else {} end)')
  results=$(jq --argjson item "$item" '. + [$item]' <<< "$results")
done

jq -n \
  --arg blueprint "$blueprint" \
  --arg root "$root" \
  --argjson repositories "$results" \
  --argjson required_failures "$required_failures" \
  '{action:"sync", blueprint:$blueprint, root:$root, repositories:$repositories, required_failures:$required_failures}'

(( required_failures == 0 )) || exit 1
