#!/bin/sh
# @spec docs/BACKLOG.md#RG-001 | docs/DAT.md#api
# Affiche l'état public du moteur (GET /health) : aucune donnée personnelle.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/common.sh"
rgpd_resolve
printf 'Moteur : %s\n' "$SAFE_URL"
if command -v curl >/dev/null 2>&1 && curl -sS --noproxy '*' --max-time 5 "$URL/health" 2>/dev/null; then
  printf '\n'
else
  printf 'Moteur injoignable.\n'
fi
if [ -n "$TOKEN" ]; then printf 'Jeton : configuré\n'; else printf 'Jeton : absent\n'; fi
printf 'Mode de repli : %s\n' "$FAIL_MODE"
