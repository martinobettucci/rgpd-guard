#!/bin/sh
# @spec docs/BACKLOG.md#RG-001 | docs/DAT.md#client-hook
# Client de hook RGPD Guard : relaie le JSON reçu de Claude Code au moteur local et recopie sa décision.
# Si le moteur ne répond pas, applique le mode de repli (closed par défaut : blocage).
# Usage : guard-hook.sh <événement> [délai_curl_en_secondes]
# Dépendances : sh POSIX, curl. Le jeton ne transite jamais en argument de commande.

EVENT="${1:-}"
MAX_TIME="${2:-20}"
umask 077

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ ! -r "$SCRIPT_DIR/common.sh" ]; then
  # Installation incomplète : on bloque plutôt que de laisser passer en silence.
  case "$EVENT" in
    user-prompt-submit) printf '{"decision":"block","reason":"RGPD Guard : installation du plugin incomplète (common.sh absent). Réinstallez le plugin."}\n' ;;
    pre-tool-use) printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"RGPD Guard : installation incomplète."}}\n' ;;
    post-tool-batch) printf '{"decision":"block","reason":"RGPD Guard : installation du plugin incomplète."}\n' ;;
    *) printf '{"systemMessage":"RGPD Guard : installation du plugin incomplète."}\n' ;;
  esac
  exit 0
fi
# shellcheck source=./common.sh
. "$SCRIPT_DIR/common.sh"
rgpd_resolve

fallback() {
  # $1 : cause courte, sans guillemets.
  cause="$1"
  start="Démarrez-le (./runProd.sh up) ou réglez le mode de repli (option fail_mode)."
  case "$FAIL_MODE:$EVENT" in
    closed:user-prompt-submit)
      printf '{"decision":"block","reason":"RGPD Guard : moteur injoignable (%s, %s). Le prompt n a pas été envoyé. %s","hookSpecificOutput":{"hookEventName":"UserPromptSubmit","suppressOriginalPrompt":true}}\n' "$SAFE_URL" "$cause" "$start"
      ;;
    closed:pre-tool-use)
      printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"RGPD Guard : moteur injoignable (%s), outil refusé tant que la protection est inactive. Demande à l utilisateur de redémarrer le moteur."}}\n' "$cause"
      ;;
    closed:post-tool-batch)
      printf '{"decision":"block","reason":"RGPD Guard : moteur injoignable (%s), boucle arrêtée avant l envoi des résultats d outils. Utilisez /rewind après avoir redémarré le moteur. %s"}\n' "$cause" "$start"
      ;;
    *)
      printf '{"systemMessage":"RGPD Guard : moteur injoignable (%s, %s), protection inactive pour cet événement. %s"}\n' "$SAFE_URL" "$cause" "$start"
      ;;
  esac
  exit 0
}

case "$EVENT" in
  session-start|user-prompt-submit|pre-tool-use|post-tool-use|post-tool-use-failure|post-tool-batch|subagent-start) ;;
  *) fallback "événement inconnu" ;;
esac

command -v curl >/dev/null 2>&1 || fallback "curl introuvable"
[ -n "$TOKEN" ] || fallback "jeton absent"

WORK_DIR="$(mktemp -d 2>/dev/null)" || fallback "dossier temporaire indisponible"
trap 'rm -rf "$WORK_DIR"' EXIT INT TERM
PAYLOAD="$WORK_DIR/payload.json"
HEADERS="$WORK_DIR/headers"
RESPONSE="$WORK_DIR/response.json"

cat > "$PAYLOAD" || fallback "lecture de l entrée impossible"
rgpd_write_headers "$HEADERS"

STATUS="$(curl -sS --noproxy '*' --max-time "$MAX_TIME" -o "$RESPONSE" -w '%{http_code}' \
  -H @"$HEADERS" --data-binary @"$PAYLOAD" "$URL/v1/hooks/$EVENT" 2>/dev/null)" || fallback "connexion impossible ou délai dépassé"

[ "$STATUS" = "200" ] || fallback "réponse HTTP $STATUS"
case "$(head -c 1 "$RESPONSE")" in
  "{") cat "$RESPONSE"; exit 0 ;;
  *) fallback "réponse illisible" ;;
esac
