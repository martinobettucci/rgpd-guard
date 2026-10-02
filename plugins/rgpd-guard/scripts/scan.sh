#!/bin/sh
# @spec docs/BACKLOG.md#RG-001 | docs/DAT.md#api
# Demande au moteur de compter les données sensibles d'un fichier (POST /v1/scan) ; seuls des comptages reviennent.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/common.sh"
rgpd_resolve
TARGET="${1:-}"
[ -n "$TARGET" ] || { printf 'Indiquez un chemin de fichier.\n'; exit 0; }
case "$TARGET" in
  /*) ABS="$TARGET" ;;
  *) ABS="$(pwd)/$TARGET" ;;
esac
umask 077
WORK_DIR="$(mktemp -d)" || exit 0
trap 'rm -rf "$WORK_DIR"' EXIT INT TERM
ESCAPED="$(printf '%s' "$ABS" | sed 's/\\/\\\\/g; s/"/\\"/g')"
printf '{"path":"%s"}' "$ESCAPED" > "$WORK_DIR/body.json"
rgpd_write_headers "$WORK_DIR/headers"
if ! curl -sS --noproxy '*' --max-time 60 -H @"$WORK_DIR/headers" --data-binary @"$WORK_DIR/body.json" "$URL/v1/scan" 2>/dev/null; then
  printf 'Moteur injoignable (%s).\n' "$SAFE_URL"
fi
printf '\n'
