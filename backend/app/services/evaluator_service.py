from __future__ import annotations
"""
Правила оценки (keyword-based) на основе файла data/evaluation_criteria.json.

Ожидаемый формат JSON (упрощённо):
{
  "criteria": [
    {"name": "backend", "keywords": ["python","fastapi"], "weight": 2},
    {"name": "db", "keywords": ["postgres","sql"], "weight": 1}
  ]
}
"""
from pathlib import Path
from typing import Any
import json

from ..config import settings


def _load_criteria() -> dict:
    """
    Загружает JSON с критериями. Возвращает {"criteria": [...]}
    Если файл отсутствует — возвращаем безопасный дефолт.
    """
    data_dir = Path(getattr(settings, "DATA_DIR", Path(__file__).resolve().parents[1] / "data"))
    path = data_dir / "evaluation_criteria.json"
    if not path.exists():
        return {"criteria": []}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def evaluate_resume(parsed: dict[str, Any]) -> dict[str, Any]:
    """
    Простая метрика: считаем количество упоминаний ключевых слов,
    умножаем на веса по аспектам, суммируем.
    """
    text = (parsed.get("text") or "").lower()
    cfg = _load_criteria()
    aspects: list[dict[str, Any]] = []
    total = 0.0

    for item in cfg.get("criteria", []):
        name = str(item.get("name") or "unnamed")
        words = [str(w).lower() for w in (item.get("keywords") or [])]
        weight = float(item.get("weight") or 1.0)

        hits = 0
        for w in words:
            if not w:
                continue
            hits += text.count(w)

        score = hits * weight
        total += score
        aspects.append({"name": name, "hits": hits, "weight": weight, "score": score})

    return {"total_score": total, "aspects": aspects}
