#!/usr/bin/env bash
# Maintain example copies inside this repository; never install into user projects.
set -Eeuo pipefail

usage() {
  cat <<'USAGE'
Usage:
  sync_examples.sh [--check]

Options:
  --check      Report drift without modifying files
  -h, --help   Show this help

Dependency: jq
USAGE
}

fail() { printf 'error: %s\n' "$*" >&2; exit 1; }
command -v jq >/dev/null 2>&1 || fail "required command not found: jq"

check=false
while (($#)); do
  case "$1" in
    --check) check=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) fail "unknown argument: $1" ;;
  esac
done

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
root=$(cd "$script_dir/.." && pwd)
manifest="$root/examples/manifest.json"
[[ -f "$manifest" ]] || fail "manifest not found: $manifest"

mismatches=()

# Emit source/destination pairs as NUL-delimited fields to preserve spaces safely.
while IFS= read -r -d '' example \
   && IFS= read -r -d '' source \
   && IFS= read -r -d '' destination; do

  src="$root/$source"
  dst="$root/examples/$example/$destination"

  # Canonicalize parent directories without requiring destination to exist.
  src_parent=$(cd "$(dirname "$src")" 2>/dev/null && pwd) || fail "source parent does not exist: $(dirname "$src")"
  src_abs="$src_parent/$(basename "$src")"
  dst_parent=$(cd "$(dirname "$dst")" 2>/dev/null && pwd || true)

  [[ $src_abs == "$root"/* ]] || fail "manifest source escapes repository: $source"

  # Lexical traversal checks for not-yet-created destinations.
  case "/$example/$destination/" in
    *'/../'*|*'/./../'* ) fail "manifest destination escapes examples/: $example/$destination" ;;
  esac
  [[ $example != /* && $destination != /* ]] || fail "manifest paths must be relative"

  [[ -f "$src_abs" ]] || fail "source file not found: $source"

  if [[ ! -f "$dst" ]] || ! cmp -s -- "$src_abs" "$dst"; then
    rel="examples/$example/$destination"
    mismatches+=("$rel")
    if [[ $check == false ]]; then
      mkdir -p -- "$(dirname "$dst")"
      cp -- "$src_abs" "$dst"
    fi
  fi
done < <(jq -j '
  to_entries[] as $example |
  $example.value | to_entries[] |
  $example.key, "\u0000", .key, "\u0000", .value, "\u0000"
' "$manifest")

if [[ $check == true ]]; then
  if ((${#mismatches[@]})); then
    printf 'Example drift:\n' >&2
    printf '%s\n' "${mismatches[@]}" >&2
    exit 1
  fi
  printf 'Examples match canonical sources\n'
else
  printf '%d example files updated\n' "${#mismatches[@]}"
fi
