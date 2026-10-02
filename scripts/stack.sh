#!/usr/bin/env bash
# @spec docs/BACKLOG.md#RG-018 | docs/DAT.md#deploiement
# Logique commune des lanceurs runDev.sh, runStaging.sh et runProd.sh.
# Usage : RGPD_STACK_ENV=<dev|staging|prod> scripts/stack.sh <commande>
# Commandes : up, down, logs, status, seed, test, e2e, bench, token, reset.
set -euo pipefail

STACK_ENV="${RGPD_STACK_ENV:?RGPD_STACK_ENV manquant}"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"

case "$STACK_ENV" in
  dev) DEFAULT_ENGINE_PORT=8742; DEFAULT_DASHBOARD_PORT=8743 ;;
  staging) DEFAULT_ENGINE_PORT=18742; DEFAULT_DASHBOARD_PORT=18743 ;;
  prod) DEFAULT_ENGINE_PORT=8742; DEFAULT_DASHBOARD_PORT=8743 ;;
  *) echo "Environnement inconnu : $STACK_ENV" >&2; exit 2 ;;
esac

export ENGINE_PORT="${ENGINE_PORT:-$DEFAULT_ENGINE_PORT}"
export DASHBOARD_PORT="${DASHBOARD_PORT:-$DEFAULT_DASHBOARD_PORT}"
export RGPD_GUARD_WORKSPACE_ROOT="${RGPD_GUARD_WORKSPACE_ROOT:-$HOME}"
export BUILD_NETWORK="${BUILD_NETWORK:-default}"
export BUILD_CA_BUNDLE="${BUILD_CA_BUNDLE:-$REPO/config/build/ca-empty.pem}"
export BUILD_HTTPS_PROXY="${BUILD_HTTPS_PROXY:-}"
ENV_FILE="config/environments/$STACK_ENV.env"
# Nom du lanceur (compatible bash 3.2 de macOS, sans ${var^}).
LAUNCHER="run$(printf '%s' "${STACK_ENV:0:1}" | tr '[:lower:]' '[:upper:]')${STACK_ENV:1}.sh"
ENGINE_URL="http://127.0.0.1:$ENGINE_PORT"
DASHBOARD_URL="http://127.0.0.1:$DASHBOARD_PORT"
CLIENT_CONFIG="$HOME/.config/rgpd-guard/engine.env"

compose() {
  docker compose -p "rgpd-guard-$STACK_ENV" -f docker-compose.yml -f "docker-compose.$STACK_ENV.yml" "$@"
}

say() { printf '\033[1m%s\033[0m\n' "$*"; }
fail() { printf 'ERREUR : %s\n' "$*" >&2; exit 1; }

require_docker() {
  command -v docker >/dev/null 2>&1 || fail "Docker est introuvable. Installez Docker et Docker Compose v2."
  docker info >/dev/null 2>&1 || fail "Le démon Docker ne répond pas. Démarrez-le puis relancez."
}

random_secret() {
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex 24
  else
    head -c 24 /dev/urandom | od -An -tx1 | tr -d ' \n'
  fi
}

env_value() {
  sed -n "s/^$1=//p" "$ENV_FILE" | tail -n 1
}

prepare_env_file() {
  if [[ "$STACK_ENV" == "dev" ]]; then
    [[ -f "$ENV_FILE" ]] || fail "$ENV_FILE est absent du dépôt."
    return
  fi
  if [[ ! -f "$ENV_FILE" ]]; then
    cp "$ENV_FILE.example" "$ENV_FILE"
    chmod 600 "$ENV_FILE"
    say "Fichier $ENV_FILE créé à partir du modèle."
  fi
  for key in RGPD_GUARD_TOKEN RGPD_GUARD_HMAC_KEY; do
    if [[ -z "$(env_value "$key")" ]]; then
      local value
      value="$(random_secret)"
      sed -i.bak "s/^$key=.*/$key=$value/" "$ENV_FILE" && rm -f "$ENV_FILE.bak"
      say "$key généré dans $ENV_FILE."
    fi
  done
}

write_client_config() {
  mkdir -p "$(dirname "$CLIENT_CONFIG")"
  umask 077
  {
    printf '# Écrit par %s : cible du plugin RGPD Guard (dernier environnement démarré).\n' "$LAUNCHER"
    printf 'RGPD_GUARD_URL=%s\n' "$ENGINE_URL"
    printf 'RGPD_GUARD_TOKEN=%s\n' "$(env_value RGPD_GUARD_TOKEN)"
  } > "$CLIENT_CONFIG"
  chmod 600 "$CLIENT_CONFIG"
}

ensure_models_cache() {
  # Dev : modèles téléchargés une fois dans models-cache/ puis montés en lecture seule.
  [[ "$STACK_ENV" == "dev" ]] || return 0
  if [[ -d models-cache/hub/models--urchade--gliner_multi_pii-v1 && -d models-cache/hub/models--convaiinnovations--laya-multilingual ]]; then
    return 0
  fi
  say "Téléchargement des modèles CPU épinglés dans models-cache/ (environ 1,9 Go, une seule fois)…"
  mkdir -p models-cache
  local ca_args=()
  if [[ -s "$BUILD_CA_BUNDLE" ]]; then
    ca_args=(-v "$BUILD_CA_BUNDLE:/ca.pem:ro" -e SSL_CERT_FILE=/ca.pem -e REQUESTS_CA_BUNDLE=/ca.pem)
  fi
  local net="bridge"
  [[ "$BUILD_NETWORK" == "host" ]] && net="host"
  docker run --rm --network "$net" -u "$(id -u):$(id -g)" -e HOME=/tmp -e HF_HUB_OFFLINE=0 \
    -e HTTPS_PROXY="$BUILD_HTTPS_PROXY" -e https_proxy="$BUILD_HTTPS_PROXY" \
    -v "$REPO/models-cache:/models-rw" ${ca_args[@]+"${ca_args[@]}"} rgpd-guard-engine:dev python -m rgpd_guard.model_store /models-rw
}

wait_healthy() {
  say "Attente du moteur (chargement des modèles, jusqu'à quelques minutes)…"
  local deadline=$((SECONDS + 600))
  until curl -fsS --noproxy '*' "$ENGINE_URL/health" >/dev/null 2>&1; do
    (( SECONDS < deadline )) || fail "le moteur ne répond pas sur $ENGINE_URL (voir : $LAUNCHER logs)"
    sleep 3
  done
}

cmd_up() {
  require_docker
  prepare_env_file
  if [[ "$STACK_ENV" == "dev" ]]; then
    compose build engine
    ensure_models_cache
  fi
  compose up -d --build
  wait_healthy
  write_client_config
  if [[ "$STACK_ENV" == "dev" ]]; then
    cmd_seed
    ensure_bench
  fi
  say "RGPD Guard ($STACK_ENV) est démarré."
  printf '  Moteur          : %s/health\n' "$ENGINE_URL"
  printf '  Tableau de bord : %s (jeton : %s token)\n' "$DASHBOARD_URL" "$LAUNCHER"
  printf '  Plugin          : /plugin marketplace add martinobettucci/rgpd-guard puis /plugin install rgpd-guard@p2enjoy\n'
  printf '  Le plugin vise désormais cet environnement (%s).\n' "$CLIENT_CONFIG"
}

ensure_bench() {
  # Dev entièrement seedé : la page Moteurs et ses E2E ont besoin d'un banc mesuré (une fois, quelques minutes).
  if compose exec -T engine test -f /data/bench/latest.json >/dev/null 2>&1; then
    return 0
  fi
  say "Premier banc d'évaluation (une seule fois, quelques minutes)…"
  cmd_bench
}

cmd_seed() {
  [[ "$STACK_ENV" != "prod" ]] || fail "aucun seed en production."
  compose --profile outils run --rm seeder
}

cmd_test() {
  require_docker
  [[ "$STACK_ENV" == "dev" ]] || fail "les tests s'exécutent dans l'environnement de développement."
  compose build engine dashboard
  # Dépôt monté en lecture seule : les contrats du client de hook ont besoin de plugins/ et de e2e/.
  compose run --rm --no-deps -e RGPD_GUARD_RELOAD=false -e PYTHONDONTWRITEBYTECODE=1 -v "$REPO:/repo:ro" engine sh -c \
    "python -m pytest -q -p no:cacheprovider tests && cd /repo/engine && python -m pytest -q -p no:cacheprovider ../e2e/claude/test_hook_client.py" || fail "tests du moteur en échec"
  compose run --rm --no-deps dashboard sh -c "npm run typecheck && npm test && npm run check:i18n && npm run check:contrast" || fail "tests du tableau de bord en échec"
  say "Tests unitaires, API et contrats : OK."
}

cmd_e2e() {
  require_docker
  [[ "$STACK_ENV" == "dev" ]] || fail "les E2E s'exécutent sur la pile de développement seedée."
  compose ps --status running engine >/dev/null 2>&1 || fail "pile arrêtée : lancez d'abord ./runDev.sh up"
  compose --profile outils run --rm e2e
  say "Captures : e2e/playwright/captures/ ; vidéos : e2e/playwright/videos/"
}

cmd_bench() {
  require_docker
  compose exec -T engine sh -c "python /seeds/generate.py --out /data/corpus.jsonl && python -m rgpd_guard.bench /data/corpus.jsonl --out /data/bench/latest.json"
}

cmd_token() {
  prepare_env_file
  env_value RGPD_GUARD_TOKEN
}

cmd_status() {
  require_docker
  compose ps
  curl -fsS --noproxy '*' "$ENGINE_URL/health" && printf '\n' || say "Moteur injoignable sur $ENGINE_URL."
}

cmd_reset() {
  require_docker
  if [[ "$STACK_ENV" != "dev" ]]; then
    printf 'Cette commande supprime le journal et la politique personnalisée de %s. Taper « %s » pour confirmer : ' "$STACK_ENV" "$STACK_ENV"
    read -r answer
    [[ "$answer" == "$STACK_ENV" ]] || fail "réinitialisation annulée."
  fi
  compose down -v
  say "Pile $STACK_ENV arrêtée et données supprimées."
}

case "${1:-}" in
  up) cmd_up ;;
  down) require_docker; compose down ;;
  logs) require_docker; compose logs -f --tail 200 ;;
  status) cmd_status ;;
  seed) require_docker; cmd_seed ;;
  test) cmd_test ;;
  e2e) cmd_e2e ;;
  bench) cmd_bench ;;
  token) cmd_token ;;
  reset) cmd_reset ;;
  *)
    printf 'Usage : %s <up|down|logs|status|seed|test|e2e|bench|token|reset>\n' "$LAUNCHER" >&2
    exit 2
    ;;
esac
