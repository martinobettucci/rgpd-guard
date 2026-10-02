# @spec docs/BACKLOG.md#RG-008 | docs/DAT.md#moteur
"""Classificateur Laya : probabilités calibrées des catégories sensibles, une seule passe sur CPU.

Les questions sont formulées en anglais simple centré sur une personne : c'est la formulation qui
sépare le mieux un cas personnel d'un texte général lors des essais consignés dans le journal.
"""

from __future__ import annotations

from typing import Any

from ..config import Settings
from ..models import CategoryScore, DetectionContext
from ..taxonomy import Category

QUESTIONS: dict[Category, str] = {
    Category.SANTE: "Does this text mention someone's illness, diagnosis, disability or medical treatment?",
    Category.OPINION_POLITIQUE: "Does this text say which political party or political opinion a person supports?",
    Category.RELIGION: "Does this text say what religion or religious belief a person has?",
    Category.ORIENTATION_SEXUELLE: "Does this text reveal a person's sexual orientation or sex life?",
    Category.ORIGINE_ETHNIQUE: "Does this text reveal a person's racial or ethnic origin?",
    Category.SYNDICAT: "Does this text say that a person is a member of a trade union?",
    Category.JUDICIAIRE: "Does this text mention a person's criminal record, conviction, arrest or trial?",
    Category.DONNEES_RH: (
        "Does this text contain HR information about a specific employee "
        "(salary, performance review, disciplinary action, dismissal)?"
    ),
    Category.MINEUR: "Does this text contain personal information about a child?",
    Category.CONFIDENTIEL: "Is the text marked or described as confidential, internal or not yet public?",
}
MAX_CHARS = 4000


class LayaClassifier:
    name = "laya"

    def __init__(self, agent: Any) -> None:
        self.agent = agent
        self.questions = {c.value: {"type": "noul", "instructions": q} for c, q in QUESTIONS.items()}

    def classify(self, text: str, ctx: DetectionContext) -> list[CategoryScore]:
        result = self.agent.system_one(text[:MAX_CHARS], self.questions)
        answers: dict[str, Any] = result.get("answers", {})
        return [
            CategoryScore(Category(key), float(answer.get("noul", 0.0)), self.name)
            for key, answer in answers.items()
            if key in Category.__members__
        ]


def load(settings: Settings) -> tuple[LayaClassifier, dict[str, str]]:
    import torch
    from laya.agent import Agent

    from ..model_store import MODELS, local_path

    torch.set_num_threads(max(1, settings.torch_threads))
    agent = Agent(local_path("laya"), device="cpu")
    return LayaClassifier(agent), {"modele": f"{MODELS['laya'].repo_id} ({MODELS['laya'].license})"}
