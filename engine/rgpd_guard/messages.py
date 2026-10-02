# @spec docs/BACKLOG.md#RG-005 | docs/BACKLOG.md#RG-006 | docs/DAT.md#flux
"""Textes affichés à l'utilisateur ou injectés à Claude. Aucun ne contient de valeur détectée en clair."""

from __future__ import annotations

from collections import Counter

from .audit import mask
from .mentions import Mention, MentionStatus
from .models import Analysis, Finding
from .taxonomy import CATEGORY_NAMES, LABEL_NAMES, Label

CUT = "8<" + "-" * 30

CLAUDE_GUIDANCE = (
    "RGPD Guard est actif sur cette session (profil {profile}). Des données personnelles ou secrètes peuvent "
    "apparaître sous forme de jetons ⟦TYPE_N⟧, par exemple ⟦EMAIL_1⟧ ou ⟦PERSONNE_2⟧. "
    "Ce sont des pseudonymes réversibles uniquement sur le poste de l'utilisateur. Règles à respecter : "
    "1) conserve chaque jeton exactement tel quel, sans le modifier, le traduire, le découper ni en inventer ; "
    "2) quand tu écris dans un fichier (Write, Edit, MultiEdit, NotebookEdit), écris le jeton : la vraie valeur "
    "est réinjectée localement ; 3) avec Edit, choisis un old_string qui ne contient aucun jeton (la validation "
    "de l'outil précède la réinjection), ou réécris le fichier entier avec Write ; 4) n'essaie jamais de deviner "
    "les valeurs réelles ; 5) ne place pas de jeton dans une commande Bash, une URL ou un appel à un outil externe : "
    "il n'y est pas réinjecté."
)

OVERSIZE_NOTE = "RGPD Guard a masqué un contenu trop volumineux pour être analysé."

EDIT_FAILURE_HINT = (
    "RGPD Guard : cet Edit a échoué parce que old_string contient un jeton ⟦...⟧ que Claude Code compare au "
    "fichier réel avant toute réinjection. Choisis un old_string sans jeton (texte voisin) ou réécris le fichier "
    "avec Write."
)


def _summary_lines(findings: list[Finding]) -> list[str]:
    grouped: dict[Label, list[Finding]] = {}
    for finding in findings:
        grouped.setdefault(finding.span.label, []).append(finding)
    lines = []
    for label, items in grouped.items():
        previews = ", ".join(sorted({mask(f.value) for f in items})[:3])
        lines.append(f"  • {LABEL_NAMES[label]} ({len(items)}) : {previews}")
    return lines


def types_summary(findings: list[Finding]) -> str:
    counts = Counter(f.span.label for f in findings)
    return ", ".join(f"{LABEL_NAMES[label]} ({n})" for label, n in counts.most_common())


def block_reason(
    analysis: Analysis,
    pseudonymized: str | None,
    mention_issues: list[Mention],
    mention_findings: list[tuple[Mention, Analysis]],
    bypass_prefix: str,
    secrets_only: bool = False,
) -> str:
    lines = ["RGPD Guard a bloqué ce prompt avant son envoi au modèle.", ""]
    if secrets_only:
        lines.append("Le préfixe de contournement ne s'applique jamais aux secrets (clés, jetons, mots de passe).")
        lines.append("")
    detected = analysis.blocking + analysis.warnings
    if detected or analysis.blocking_categories:
        lines.append("Détecté dans le prompt :")
        lines += _summary_lines(detected)
        for cat in analysis.blocking_categories:
            lines.append(
                f"  • catégorie sensible : {CATEGORY_NAMES[cat.score.category]} "
                f"(probabilité {cat.score.probability:.2f}), associée à un identifiant"
            )
        lines.append("")
    for mention, sub in mention_findings:
        lines.append(f"Détecté dans le fichier mentionné @{mention.raw} :")
        lines += _summary_lines(sub.blocking)
        lines.append("")
    for mention in mention_issues:
        reason = {
            MentionStatus.OUT_OF_REACH: "hors du dossier que RGPD Guard peut lire",
            MentionStatus.BINARY: "fichier non textuel (image, PDF...) que RGPD Guard ne peut pas analyser",
            MentionStatus.TOO_LARGE: "fichier trop volumineux pour être analysé",
        }.get(mention.status, "non vérifiable")
        lines.append(f"Mention @{mention.raw} : {reason}.")
    if mention_issues or mention_findings:
        lines.append(
            "Le contenu d'un fichier mentionné par @ est envoyé tel quel au modèle. Retirez la mention et demandez "
            "plutôt à Claude de lire le fichier : sa sortie sera pseudonymisée."
        )
        lines.append("")
    if pseudonymized is not None:
        lines.append("Version pseudonymisée, prête à copier :")
        lines.append(CUT)
        lines.append(pseudonymized)
        lines.append(CUT)
        lines.append(
            "Les jetons ⟦...⟧ sont réinjectés localement si Claude les écrit dans un fichier ; le modèle ne "
            "voit jamais les vraies valeurs."
        )
    if not secrets_only:
        lines.append(f"Pour envoyer malgré tout (hors secrets), commencez le prompt par {bypass_prefix}.")
    return "\n".join(lines).rstrip()


def warning_message(analysis: Analysis) -> str:
    parts = []
    if analysis.warnings:
        parts.append(types_summary(analysis.warnings))
    for cat in analysis.warning_categories:
        parts.append(f"catégorie {CATEGORY_NAMES[cat.score.category]} ({cat.score.probability:.2f})")
    return "RGPD Guard (avertissement, prompt envoyé) : " + "; ".join(parts) + "."


def bypass_message(count: int) -> str:
    return f"RGPD Guard : contournement utilisé, {count} donnée(s) envoyée(s) au modèle. L'événement est journalisé."


def output_note(findings: list[Finding]) -> str:
    return (
        f"RGPD Guard a remplacé {len(findings)} valeur(s) de ce résultat par des jetons ⟦...⟧ "
        f"({types_summary(findings)}). Conserve ces jetons tels quels."
    )


def batch_block_reason(findings: list[Finding]) -> str:
    return (
        "RGPD Guard a arrêté la boucle avant l'envoi au modèle : une sortie d'outil contient encore des données "
        f"sensibles qui n'ont pas pu être masquées ({types_summary(findings)}). Le résultat reste dans la "
        "conversation locale : utilisez /rewind (ou Échap deux fois) pour revenir avant cet appel d'outil avant de "
        "continuer."
    )


def unknown_token_reason(tokens: list[str]) -> str:
    sample = ", ".join(sorted(set(tokens))[:5])
    return (
        f"RGPD Guard : jeton(s) inconnu(s) {sample} (session expirée ou moteur redémarré). Aucun jeton ne doit être "
        "écrit dans un fichier : relis le fichier source pour obtenir des jetons valides, puis recommence."
    )


def secret_file_reason(path: str) -> str:
    return (
        f"RGPD Guard : lecture refusée, « {path} » est un fichier de secrets. Demande à l'utilisateur les seules "
        "informations non sensibles dont tu as besoin."
    )


def engine_degraded_message(missing: list[str], profile: str) -> str:
    return (
        f"RGPD Guard : profil {profile} incomplet, composants indisponibles : {', '.join(missing)}. "
        "La détection continue avec les détecteurs disponibles."
    )
