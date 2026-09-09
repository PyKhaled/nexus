#!/usr/bin/env bash
# Literal env-file loader. Compatible with macOS Bash 3.2 and Linux Bash.
set -euo pipefail

fail() { printf 'config: %s\n' "$*" >&2; exit 1; }
root=$(cd "$(dirname "$0")/.." && pwd)
action=${1:-}; shift || true
stage=${NEXUS_ENV:-development}
case "$stage" in development|production) ;; *) fail 'ENV must be development or production' ;; esac
runtime=${NEXUS_CONFIG_DIR:-}
if [[ -z "$runtime" ]]; then
    if [[ "$stage" == production ]]; then runtime=/etc/nexus
    else runtime="$root/.env/development"; fi
fi
[[ "$runtime" == /* ]] || runtime="$PWD/$runtime"

# No values are printed, sourced, evaluated, or placed in command arguments.
keys=(); values=()
parse() {
    local file=$1 line key value quote n=0 i mode
    [[ -f "$file" && ! -L "$file" && -r "$file" ]] || fail "not a readable regular file: $file"
    mode=$(stat -c '%a' "$file" 2>/dev/null || stat -f '%Lp' "$file")
    # Allow 600 and 640; never world access, group writes, or executable bits.
    (( (8#$mode & 07137) == 0 )) || fail "unsafe permissions on $file; use chmod 600 (or 640)"
    local seen=' '
    while IFS= read -r line || [[ -n "$line" ]]; do
        n=$((n + 1)); line=${line%$'\r'}
        [[ "$line" =~ ^[[:space:]]*$ || "$line" =~ ^[[:space:]]*# ]] && continue
        [[ "$line" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]] || fail "$file:$n: expected KEY=value"
        key=${line%%=*}; value=${line#*=}
        [[ "$seen" != *" $key "* ]] || fail "$file:$n: duplicate key $key"
        seen="$seen$key "
        quote=${value:0:1}
        if [[ "$quote" == \" || "$quote" == "'" ]]; then
            [[ ${#value} -ge 2 && "${value: -1}" == "$quote" ]] || fail "$file:$n: unmatched quote"
            value=${value:1:${#value}-2}
        fi
        # Override previous files, retaining explicit inherited environment values later.
        for ((i=0; i<${#keys[@]}; i++)); do
            [[ "${keys[i]}" == "$key" ]] && break
        done
        keys[i]=$key; values[i]=$value
    done < "$file"
}

load() {
    # Existing component files and root secrets remain development-only fallbacks.
    if [[ "$stage" == development ]]; then
        local file
        for file in "$root/system/system-auth/.env" "$root/system/system-auth-db/.env" "${SECRETS_ENV:-$root/secrets.env}"; do
            [[ ! -e "$file" && ! -L "$file" ]] || parse "$file"
        done
    fi
    if [[ -e "$runtime/config.env" || -L "$runtime/config.env" || -e "$runtime/secret.env" || -L "$runtime/secret.env" || "$stage" == production || "$action" == check ]]; then
        parse "$runtime/config.env"
        parse "$runtime/secret.env"
    fi
}

case "$action" in
    init)
        [[ ! -L "$runtime" ]] || fail 'runtime directory must not be a symlink'
        umask 077
        mkdir -p "$runtime"
        for name in config secret; do
            destination="$runtime/$name.env"
            if [[ -e "$destination" || -L "$destination" ]]; then
                printf 'Kept %s\n' "$destination"
            else
                # noclobber prevents overwriting a file created concurrently.
                (set -o noclobber; cat "$root/config/compose/$name.env.example" > "$destination")
                printf 'Created %s\n' "$destination"
            fi
        done
        ;;
    path) printf 'Configuration: %s/config.env\nSecrets: %s/secret.env\n' "$runtime" "$runtime" ;;
    check) load; printf 'Configuration syntax and permissions valid (%s).\n' "$stage" ;;
    run)
        [[ "${1:-}" != -- ]] || shift
        [[ $# -gt 0 ]] || fail 'run requires a command after --'
        load
        # Export only in a child shell. Avoid env KEY=value command arguments.
        # Preserve empty inherited values too. Reserve shell/loader control variables.
        for ((i=0; i<${#keys[@]}; i++)); do
            case "${keys[i]}" in
                PATH|HOME|SHELL|ENV|BASH*|SHELLOPTS|BASHOPTS|IFS|CDPATH|LD_*|DYLD_*|NEXUS_*|keys|values|i|root|runtime|action|stage)
                    fail "reserved environment key: ${keys[i]}" ;;
            esac
        done
        for ((i=0; i<${#keys[@]}; i++)); do
            if ! printenv "${keys[i]}" >/dev/null; then export "${keys[i]}=${values[i]}"; fi
        done
        exec "$@"
        ;;
    *) fail 'usage: scripts/config.sh {init|path|check|run -- COMMAND ...}' ;;
esac
