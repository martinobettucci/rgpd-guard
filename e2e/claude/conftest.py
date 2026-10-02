# @spec docs/BACKLOG.md#RG-001 | docs/DAT.md#flux-hooks
# @verifies docs/BACKLOG.md#RG-001 | docs/DAT.md#flux-hooks
"""Rend le harnais importable depuis les tests E2E de Claude Code."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
