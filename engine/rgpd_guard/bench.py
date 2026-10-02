# @spec docs/BACKLOG.md#RG-017 | docs/BACKLOG.md#RG-016 | docs/DAT.md#profils
"""Banc d'évaluation : précision, rappel et F1 par type et par profil, catégories, latences p50/p95.

Usage : python -m rgpd_guard.bench <corpus.jsonl> [--out <fichier.json>] [--profiles rapide,equilibre,max]
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import Settings
from .models import Context
from .pipeline import PROFILES
from .service import Engine


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round(q * (len(ordered) - 1))))
    return round(ordered[index], 1)


def _overlap(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return bool(a["start"] < b["end"] and b["start"] < a["end"] and a["label"] == b["label"])


def _prf(tp: int, fp: int, fn: int) -> dict[str, float | int]:
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
    }


def evaluate(engine: Engine, records: list[dict[str, Any]], profile: str) -> dict[str, Any]:
    counts: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
    cat_counts: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
    latencies: list[float] = []
    thresholds = {c.value: r.threshold for c, r in engine.policy.categories.items()}
    errors: list[dict[str, Any]] = []
    uses_categories = bool(PROFILES[profile].classifiers_prompt)
    for record in records:
        started = time.perf_counter()
        analysis = engine.pipeline.analyze(record["text"], profile, Context.PROMPT, bool(record.get("code")))
        latencies.append((time.perf_counter() - started) * 1000)
        predicted: list[dict[str, Any]] = [
            {"start": f.span.start, "end": f.span.end, "label": f.span.label.value} for f in analysis.findings
        ]
        expected = record["spans"]
        matched_pred: set[int] = set()
        for exp in expected:
            hit = next((i for i, p in enumerate(predicted) if i not in matched_pred and _overlap(exp, p)), None)
            if hit is None:
                counts[exp["label"]][2] += 1
                errors.append({"id": record["id"], "profil": profile, "type": "manqué", "label": exp["label"]})
            else:
                matched_pred.add(hit)
                counts[exp["label"]][0] += 1
        for i, pred in enumerate(predicted):
            if i not in matched_pred:
                counts[pred["label"]][1] += 1
                errors.append({"id": record["id"], "profil": profile, "type": "faux positif", "label": pred["label"]})
        if uses_categories:
            raw = {c.score.category.value for c in analysis.categories}
            for category in thresholds:
                expected_cat = category in record.get("categories", [])
                predicted_cat = category in raw
                if expected_cat and predicted_cat:
                    cat_counts[category][0] += 1
                elif predicted_cat:
                    cat_counts[category][1] += 1
                elif expected_cat:
                    cat_counts[category][2] += 1
    total = [sum(v[i] for v in counts.values()) for i in range(3)]
    return {
        "profile": profile,
        "records": len(records),
        "global": _prf(*total),
        "by_label": {label: _prf(*v) for label, v in sorted(counts.items())},
        "categories": {c: _prf(*v) for c, v in sorted(cat_counts.items())} if uses_categories else {},
        "latency_ms": {
            "p50": _percentile(latencies, 0.5),
            "p95": _percentile(latencies, 0.95),
            "mean": round(statistics.fmean(latencies), 1) if latencies else 0.0,
        },
        "errors": errors[:200],
    }


def run(corpus: Path, profiles: list[str], settings: Settings) -> dict[str, Any]:
    records = [json.loads(line) for line in corpus.read_text(encoding="utf-8").splitlines() if line.strip()]
    engine = Engine(settings)
    available = [p for p in profiles if not engine.registry.missing_for_name(p)]
    for profile in available:  # échauffement : la première inférence d'un modèle est plus lente
        engine.pipeline.analyze(records[0]["text"], profile)
    results = [evaluate(engine, records, p) for p in available]
    engine.store.close()
    return {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "corpus": {"path": corpus.name, "records": len(records)},
        "torch_threads": settings.torch_threads,
        "skipped_profiles": [p for p in profiles if p not in available],
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("corpus", type=Path)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--profiles", default="rapide,equilibre,max")
    args = parser.parse_args()
    settings = Settings(token="banc", hmac_key="banc")  # noqa: S106 (le banc n'expose aucune API)
    report = run(args.corpus, args.profiles.split(","), settings)
    out = args.out or settings.data_dir / "bench" / "latest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    for result in report["results"]:
        g = result["global"]
        lat = result["latency_ms"]
        print(
            f"{result['profile']:<10} P={g['precision']:.3f} R={g['recall']:.3f} F1={g['f1']:.3f} p50={lat['p50']} ms p95={lat['p95']} ms"
        )
    print(f"rapport : {out}")


if __name__ == "__main__":
    main()
