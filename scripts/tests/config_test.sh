#!/usr/bin/env bash
set -euo pipefail
umask 077
root=$(cd "$(dirname "$0")/../.." && pwd)
scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT
# Isolate legacy paths from the real checkout; never read user credentials.
mkdir -p "$scratch/repo/scripts" "$scratch/repo/config"
cp "$root/scripts/config.sh" "$scratch/repo/scripts/config.sh"
cp -R "$root/config/compose" "$scratch/repo/config/compose"
helper="$scratch/repo/scripts/config.sh"
export NEXUS_CONFIG_DIR="$scratch/runtime with spaces" NEXUS_ENV=development
unset SECRETS_ENV
run() { "$BASH" "$helper" "$@"; }
fail() { echo "FAIL: $*" >&2; exit 1; }
reject() {
    if run "$@" >"$scratch/output" 2>&1; then fail "accepted invalid input: $*"; fi
}
run init >/dev/null
[[ -f "$NEXUS_CONFIG_DIR/config.env" && -f "$NEXUS_CONFIG_DIR/secret.env" ]] || fail init
run check >/dev/null
run run -- true
printf 'SHARED=configuration\nLITERAL=\x27$(touch %s/pwned) $HOME `id` # literal\x27\nEMPTY=file\n' "$scratch" > "$NEXUS_CONFIG_DIR/config.env"
printf 'SHARED=secret\nPASSWORD="test $dollar # spaces"\n' > "$NEXUS_CONFIG_DIR/secret.env"
run init >/dev/null
run run -- bash -c '[[ $SHARED == secret && $PASSWORD == "test \$dollar # spaces" ]]'
[[ ! -e "$scratch/pwned" ]] || fail 'executed config contents'
SHARED=process EMPTY='' run run -- bash -c '[[ $SHARED == process && $EMPTY == "" ]]'
run run -- bash -c '[[ $LITERAL == *"\$HOME"* ]]'
set +e
run run -- bash -c 'exit 23'
status=$?
set -e
[[ $status == 23 ]] || fail 'lost child exit code'
printf 'BAD LINE secret-value\n' >> "$NEXUS_CONFIG_DIR/secret.env"
reject check
! grep -q secret-value "$scratch/output" || fail 'leaked malformed value'
printf 'KEY=one\nKEY=two\n' > "$NEXUS_CONFIG_DIR/secret.env"
reject check
printf 'KEY="unclosed\n' > "$NEXUS_CONFIG_DIR/secret.env"
reject check
printf 'KEY=value\r\n' > "$NEXUS_CONFIG_DIR/secret.env"
run check >/dev/null
chmod 644 "$NEXUS_CONFIG_DIR/secret.env"
reject check
chmod 640 "$NEXUS_CONFIG_DIR/secret.env"
run check >/dev/null
printf 'PATH=/tmp\n' > "$NEXUS_CONFIG_DIR/secret.env"
reject run -- true
rm "$NEXUS_CONFIG_DIR/secret.env"
ln -s "$NEXUS_CONFIG_DIR/config.env" "$NEXUS_CONFIG_DIR/secret.env"
reject check
rm "$NEXUS_CONFIG_DIR/secret.env"
reject check
NEXUS_ENV=staging reject path
NEXUS_ENV=production NEXUS_CONFIG_DIR='' run path | grep -q /etc/nexus/secret.env
NEXUS_ENV=production NEXUS_CONFIG_DIR="$scratch/missing" reject run -- true
# No private files are needed for default development startup.
NEXUS_CONFIG_DIR="$scratch/missing" run run -- true
mkdir -p "$scratch/dangling"
ln -s "$scratch/not-there" "$scratch/dangling/config.env"
NEXUS_CONFIG_DIR="$scratch/dangling" reject run -- true
# Legacy files are lower priority, and are excluded in production.
printf 'LEGACY_ONLY=legacy\nSHARED=legacy\n' > "$scratch/repo/secrets.env"
chmod 600 "$scratch/repo/secrets.env"
printf 'SHARED=current\n' > "$NEXUS_CONFIG_DIR/secret.env"
run run -- bash -c '[[ $LEGACY_ONLY == legacy && $SHARED == current ]]'
NEXUS_ENV=production run run -- bash -c '[[ ${LEGACY_ONLY-unset} == unset ]]'
echo 'Bash configuration tests passed.'
