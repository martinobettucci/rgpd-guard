# @spec docs/BACKLOG.md#RG-005 | docs/BACKLOG.md#RG-006 | docs/BACKLOG.md#RG-004 | docs/DAT.md#flux | docs/DAT.md#flux-hooks
"""Adaptateurs des événements de hook Claude Code : JSON reçu, JSON de décision renvoyé."""

from __future__ import annotations

import copy
import time
from collections.abc import Callable
from typing import Any

from . import messages
from .audit import AuditRecord, Store, decision_of
from .mentions import MentionStatus, resolve_mentions
from .models import Action, Analysis, Context, Finding
from .pipeline import Pipeline
from .pseudonymizer import contains_token, pseudonymize, rehydrate
from .textutil import TOKEN_RE, is_code_path
from .vault import Vault
from .walker import iter_strings, walk

WRITE_TOOLS = frozenset({"Write", "Edit", "MultiEdit", "NotebookEdit"})
PATH_TOOLS = frozenset({"Read", "Grep", "Glob", "LS"})
# Champs réhydratés par outil ; jamais de réhydratation vers Bash, WebFetch, WebSearch ni MCP.
REHYDRATE_FIELDS: dict[str, tuple[str, ...]] = {
    "Write": ("content",),
    "Edit": ("old_string", "new_string"),
    "MultiEdit": ("edits",),
    "NotebookEdit": ("new_source",),
    "Read": ("file_path",),
    "Grep": ("pattern", "path", "glob"),
    "Glob": ("pattern", "path"),
    "LS": ("path",),
}
EVENTS = (
    "session-start",
    "user-prompt-submit",
    "pre-tool-use",
    "post-tool-use",
    "post-tool-use-failure",
    "post-tool-batch",
    "subagent-start",
)


class HookAdapter:
    def __init__(
        self,
        pipeline: Pipeline,
        vault: Vault,
        store: Store,
        default_profile: str,
        bypass_prefix: str,
        workspace_root: Any,
        max_text_chars: int,
    ) -> None:
        self.pipeline = pipeline
        self.vault = vault
        self.store = store
        self.default_profile = default_profile
        self.bypass_prefix = bypass_prefix
        self.workspace_root = workspace_root
        self.max_text_chars = max_text_chars
        self._handlers: dict[str, Callable[[dict[str, Any], str], dict[str, Any]]] = {
            "session-start": self.session_start,
            "subagent-start": self.subagent_start,
            "user-prompt-submit": self.user_prompt_submit,
            "pre-tool-use": self.pre_tool_use,
            "post-tool-use": self.post_tool_use,
            "post-tool-use-failure": self.post_tool_use_failure,
            "post-tool-batch": self.post_tool_batch,
        }

    def handle(self, event: str, payload: dict[str, Any], profile: str | None = None) -> dict[str, Any]:
        handler = self._handlers.get(event)
        if handler is None:
            return {}
        return handler(payload, profile or self.default_profile)

    # Contexte ---------------------------------------------------------------------------------
    def _guidance(self, event_name: str, profile: str) -> dict[str, Any]:
        output: dict[str, Any] = {
            "hookSpecificOutput": {
                "hookEventName": event_name,
                "additionalContext": messages.CLAUDE_GUIDANCE.format(profile=profile),
            }
        }
        missing = self.pipeline.registry.missing_for_name(profile)
        if missing and event_name == "SessionStart":
            output["systemMessage"] = messages.engine_degraded_message(missing, profile)
        return output

    def session_start(self, payload: dict[str, Any], profile: str) -> dict[str, Any]:
        return self._guidance("SessionStart", profile)

    def subagent_start(self, payload: dict[str, Any], profile: str) -> dict[str, Any]:
        return self._guidance("SubagentStart", profile)

    # Prompt ------------------------------------------------------------------------------------
    def user_prompt_submit(self, payload: dict[str, Any], profile: str) -> dict[str, Any]:
        started = time.perf_counter()
        session_id = str(payload.get("session_id", ""))
        prompt = str(payload.get("prompt", ""))
        bypass = prompt.lstrip().startswith(self.bypass_prefix)
        analysis = self.pipeline.analyze(prompt, profile, Context.PROMPT)

        mention_issues = []
        mention_findings: list[tuple[Any, Analysis]] = []
        mention_all: list[Finding] = []
        for mention in resolve_mentions(prompt, str(payload.get("cwd", "")), self.workspace_root):
            if mention.status in (MentionStatus.OUT_OF_REACH, MentionStatus.BINARY, MentionStatus.TOO_LARGE):
                mention_issues.append(mention)
            elif mention.status is MentionStatus.TEXT:
                sub = self.pipeline.analyze(mention.content, profile, Context.PROMPT, is_code_path(mention.path))
                mention_all += sub.findings
                if sub.is_blocking:
                    mention_findings.append((mention, sub))

        excluded_labels = set(self.pipeline.policy.policy.bypass_excluded)
        all_findings = analysis.findings + mention_all
        secrets = [f for f in all_findings if f.span.label in excluded_labels]
        record = AuditRecord(
            session_id=session_id,
            event="user_prompt_submit",
            decision=decision_of(analysis),
            profile=analysis.profile,
            latency_ms=0.0,
            findings=all_findings,
            categories=_categories(analysis),
            subagent=bool(payload.get("agent_id")),
            bypass=bypass,
            partial=analysis.partial,
        )

        blocked = analysis.is_blocking or bool(mention_issues) or bool(mention_findings)
        if bypass and not secrets:
            record.decision = Action.ALLOW.value if not all_findings else Action.WARN.value
            record.note = "contournement"
            self._audit(record, started)
            return {"systemMessage": messages.bypass_message(len(all_findings))} if all_findings else {}
        if blocked or (bypass and secrets):
            proposal = None
            if analysis.to_pseudonymize:
                proposal = pseudonymize(prompt, analysis.to_pseudonymize, self.vault, session_id)
                if bypass:
                    proposal = proposal.lstrip()[len(self.bypass_prefix) :].lstrip()
            reason = messages.block_reason(
                analysis,
                proposal,
                mention_issues,
                mention_findings,
                self.bypass_prefix,
                secrets_only=bypass and bool(secrets),
            )
            record.decision = Action.BLOCK.value
            record.note = "mention @ non vérifiable" if mention_issues else None
            self._audit(record, started)
            return {
                "decision": "block",
                "reason": reason,
                "hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "suppressOriginalPrompt": True},
            }
        self._audit(record, started)
        if analysis.warnings or analysis.warning_categories:
            return {"systemMessage": messages.warning_message(analysis)}
        return {}

    # Outils ------------------------------------------------------------------------------------
    def pre_tool_use(self, payload: dict[str, Any], profile: str) -> dict[str, Any]:
        started = time.perf_counter()
        tool = str(payload.get("tool_name", ""))
        tool_input = payload.get("tool_input") or {}
        session_id = str(payload.get("session_id", ""))
        if tool == "Read" and isinstance(tool_input, dict):
            path = str(tool_input.get("file_path", ""))
            if path and self.pipeline.policy.is_secret_file(path):
                self._audit(
                    AuditRecord(session_id, "pre_tool_use", "deny", profile, 0.0, tool=tool, note="fichier secret"),
                    started,
                )
                return _deny(messages.secret_file_reason(path))
        fields = REHYDRATE_FIELDS.get(tool)
        if not fields or not isinstance(tool_input, dict):
            return {}
        updated = copy.deepcopy(tool_input)
        replaced = 0
        unknown: list[str] = []

        def _rehydrate(text: str) -> tuple[str, int]:
            nonlocal replaced
            if not contains_token(text):
                return text, 0
            result = rehydrate(text, self.vault, session_id)
            unknown.extend(result.unknown)
            replaced += result.replaced
            return result.text, result.replaced

        for name in fields:
            if name in updated:
                updated[name], _ = walk_all(updated[name], _rehydrate)
        if unknown:
            self._audit(
                AuditRecord(session_id, "pre_tool_use", "deny", profile, 0.0, tool=tool, note="jeton inconnu"),
                started,
            )
            return _deny(messages.unknown_token_reason(unknown))
        if not replaced:
            return {}
        self._audit(
            AuditRecord(session_id, "pre_tool_use", "rehydrate", profile, 0.0, tool=tool, note=f"{replaced} jeton(s)"),
            started,
        )
        # updatedInput sans permissionDecision : les règles de permission normales s'appliquent (mesuré, M1).
        return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "updatedInput": updated}}

    def post_tool_use(self, payload: dict[str, Any], profile: str) -> dict[str, Any]:
        started = time.perf_counter()
        tool = str(payload.get("tool_name", ""))
        if tool in WRITE_TOOLS or "tool_response" not in payload:
            return {}
        session_id = str(payload.get("session_id", ""))
        tool_input = payload.get("tool_input") if isinstance(payload.get("tool_input"), dict) else {}
        code_mode = tool == "Bash" and profile != "max" or is_code_path(str((tool_input or {}).get("file_path", "")))
        found: list[Finding] = []
        partial = False

        def _transform(text: str) -> tuple[str, int]:
            nonlocal partial
            if len(text) > self.max_text_chars:
                partial = True
                return f"[RGPD Guard : contenu de {len(text)} caractères masqué, trop volumineux pour être analysé]", 1
            analysis = self.pipeline.analyze(text, profile, Context.TOOL_OUTPUT, code_mode)
            partial = partial or analysis.partial
            targets = analysis.to_pseudonymize
            if not targets:
                return text, 0
            found.extend(targets)
            return pseudonymize(text, targets, self.vault, session_id), len(targets)

        new_response, count = walk(payload["tool_response"], _transform)
        if not count:
            return {}
        self._audit(
            AuditRecord(
                session_id,
                "post_tool_use",
                Action.PSEUDONYMIZE.value,
                profile,
                0.0,
                findings=found,
                tool=tool,
                subagent=bool(payload.get("agent_id")),
                partial=partial,
            ),
            started,
        )
        return {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "updatedToolOutput": new_response,
                "additionalContext": messages.output_note(found) if found else messages.OVERSIZE_NOTE,
            }
        }

    def post_tool_use_failure(self, payload: dict[str, Any], profile: str) -> dict[str, Any]:
        started = time.perf_counter()
        tool = str(payload.get("tool_name", ""))
        session_id = str(payload.get("session_id", ""))
        error = str(payload.get("error", ""))
        analysis = self.pipeline.analyze(error[: self.max_text_chars], "rapide", Context.TOOL_OUTPUT, True)
        if analysis.to_pseudonymize:
            self._audit(
                AuditRecord(
                    session_id,
                    "post_tool_use_failure",
                    "leak",
                    "rapide",
                    0.0,
                    findings=analysis.to_pseudonymize,
                    tool=tool,
                    note="sortie d'échec contenant des données, arrêtée par le filet PostToolBatch",
                ),
                started,
            )
        if tool in ("Edit", "MultiEdit") and TOKEN_RE.search(str(payload.get("tool_input", ""))):
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUseFailure",
                    "additionalContext": messages.EDIT_FAILURE_HINT,
                }
            }
        return {}

    def post_tool_batch(self, payload: dict[str, Any], profile: str) -> dict[str, Any]:
        started = time.perf_counter()
        session_id = str(payload.get("session_id", ""))
        residual: list[Finding] = []
        tools: list[str] = []
        for call in payload.get("tool_calls") or []:
            if not isinstance(call, dict):
                continue
            for text in iter_strings(call.get("tool_response")):
                analysis = self.pipeline.analyze(text[: self.max_text_chars], "rapide", Context.TOOL_OUTPUT, True)
                if analysis.to_pseudonymize:
                    residual += analysis.to_pseudonymize
                    tools.append(str(call.get("tool_name", "")))
        if not residual:
            return {}
        self._audit(
            AuditRecord(
                session_id,
                "post_tool_batch",
                "leak",
                "rapide",
                0.0,
                findings=residual,
                tool=",".join(sorted(set(tools))),
                note="boucle arrêtée avant envoi",
            ),
            started,
        )
        return {"decision": "block", "reason": messages.batch_block_reason(residual)}

    # Journal -----------------------------------------------------------------------------------
    def _audit(self, record: AuditRecord, started: float) -> None:
        record.latency_ms = (time.perf_counter() - started) * 1000
        self.store.record(record)


def walk_all(value: Any, transform: Callable[[str], tuple[str, int]]) -> tuple[Any, int]:
    """Comme walker.walk, sans ignorer les clés techniques (chemins à réhydrater compris)."""
    if isinstance(value, str):
        return transform(value)
    if isinstance(value, list):
        out, total = [], 0
        for item in value:
            new, n = walk_all(item, transform)
            out.append(new)
            total += n
        return out, total
    if isinstance(value, dict):
        result, total = {}, 0
        for key, item in value.items():
            result[key], n = walk_all(item, transform)
            total += n
        return result, total
    return value, 0


def _deny(reason: str) -> dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def _categories(analysis: Analysis) -> list[dict[str, Any]]:
    return [
        {"category": c.score.category.value, "probability": round(c.score.probability, 3), "action": c.action.value}
        for c in analysis.categories
    ]
