# Registre d'incohérences

Défauts constatés hors de l'unité en cours, à résoudre par la boucle dédiée (CLAUDE.md §5) dans l'ordre ci-dessous. Chaque entrée quitte le registre avec son issue : corrigée, tranchée sans changement (motif au [journal](JOURNAL.md)) ou convertie en unité du [backlog](BACKLOG.md).

Origine : audit en lecture seule de la v0.1.0 avant la campagne de clôture, constats revérifiés à la main.

## IR-14 Références `@spec` sans section

- Constat : `dashboard/src/pages/Sandbox.tsx:1`, `dashboard/src/i18n/index.ts:1`, `dashboard/index.html:2` et `dashboard/scripts/check-i18n.mjs:1` citent `docs/DESIGN_SYSTEM.md` sans chapitre, contrairement à CLAUDE.md §5 ; `scripts/check-spec-refs` ne contrôle que les références ancrées et laisse passer.
- Concerne : RG-000, RG-013, RG-014.

## IR-15 `THIRD_PARTY_NOTICES.md` incomplet

- Constat : les dépendances npm livrées dans l'image du tableau de bord (React, React Router, Lucide) et l'image de base nginx n'y figurent pas.
- Concerne : RG-013, RG-018.

## IR-16 Dérives de documentation

- Constat :
  - README « État du projet » : « implémenté, vérifié en E2E » alors que le BACKLOG garde toutes les unités à `[~]` ;
  - README : `./runDev.sh test` présenté comme « toute la batterie », alors qu'il n'exécute ni l'E2E Claude Code, ni les harnais des lanceurs et des hooks ;
  - arborescence du README sans `tests/launchers/` ni `config/` ;
  - BACKLOG RG-001 : chemin `scripts/guard-hook.sh` au lieu de `plugins/rgpd-guard/scripts/guard-hook.sh` ;
  - JOURNAL (décisions du cadrage) : environnements exécutables côte à côte, alors que dev et prod partagent les ports 8742 et 8743.
- Concerne : README, BACKLOG, JOURNAL.

## IR-17 Version 0.1.0 absente du CHANGELOG et de la marketplace

- Constat : les manifestes portent tous 0.1.0, le CHANGELOG n'a pas d'entrée 0.1.0 et l'entrée du plugin dans `.claude-plugin/marketplace.json` n'a pas de version.
- Concerne : RG-001, CHANGELOG.
