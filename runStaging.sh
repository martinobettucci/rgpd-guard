#!/usr/bin/env bash
# @spec docs/BACKLOG.md#RG-018 | docs/DAT.md#deploiement
# Lanceur de l'environnement staging. Voir README.md, section « Lancer la pile ».
exec env RGPD_STACK_ENV=staging "$(cd "$(dirname "$0")" && pwd)/scripts/stack.sh" "$@"
