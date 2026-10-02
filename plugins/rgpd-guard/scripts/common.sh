# @spec docs/BACKLOG.md#RG-001 | docs/DAT.md#client-hook
# Résolution partagée de la cible du moteur (sourcé par les scripts du plugin, jamais exécuté seul).
# Priorité : options du plugin, variables RGPD_GUARD_*, fichier écrit par le dernier lanceur, valeurs par défaut.

rgpd_config_value() {
  [ -r "$RGPD_CONFIG_FILE" ] || return 0
  sed -n "s/^$1=//p" "$RGPD_CONFIG_FILE" | tail -n 1 | tr -d '\r'
}

rgpd_resolve() {
  RGPD_CONFIG_FILE="${RGPD_GUARD_CONFIG:-$HOME/.config/rgpd-guard/engine.env}"
  URL="${CLAUDE_PLUGIN_OPTION_ENGINE_URL:-${RGPD_GUARD_URL:-}}"
  [ -n "$URL" ] || URL="$(rgpd_config_value RGPD_GUARD_URL)"
  [ -n "$URL" ] || URL="http://127.0.0.1:8742"
  TOKEN="${CLAUDE_PLUGIN_OPTION_ENGINE_TOKEN:-${RGPD_GUARD_TOKEN:-}}"
  [ -n "$TOKEN" ] || TOKEN="$(rgpd_config_value RGPD_GUARD_TOKEN)"
  FAIL_MODE="${CLAUDE_PLUGIN_OPTION_FAIL_MODE:-${RGPD_GUARD_FAIL_MODE:-closed}}"
  PROFILE="${CLAUDE_PLUGIN_OPTION_PROFILE:-${RGPD_GUARD_PROFILE:-}}"
  [ "$PROFILE" = "defaut" ] && PROFILE=""
  SAFE_URL="$(printf '%s' "$URL" | tr -d '"\\')"
}

# Écrit les en-têtes (dont le jeton) dans un fichier, pour ne jamais passer le jeton en argument.
rgpd_write_headers() {
  {
    printf 'Content-Type: application/json\n'
    printf 'X-RGPD-Guard-Token: %s\n' "$TOKEN"
    [ -n "$PROFILE" ] && printf 'X-RGPD-Guard-Profile: %s\n' "$PROFILE"
  } > "$1"
}
