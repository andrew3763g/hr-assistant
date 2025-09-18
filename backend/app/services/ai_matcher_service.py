from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence, cast

from openai import OpenAI, OpenAIError

try:
    from backend.app.config import settings  # type: ignore
except Exception:  # pragma: no cover
    settings = None  # noqa: N816

from backend.app.services.api_key_manager import APIKeyManager

__all__ = ["rank_candidates"]


_DEFAULT_WEIGHTS: dict[str, float] = {
    "skills": 4,
    "recent": 3,
    "communication": 2,
    "culture": 1,
}


@dataclass(frozen=True)
class PreparedCandidate:
    index: int
    candidate_id: str
    name: str
    text: str


@dataclass(frozen=True)
class RankedCandidate:
    index: int
    candidate_id: str
    name: str
    score: int
    reasons: str


def _get_passphrase(explicit: Optional[str] = None) -> Optional[str]:
    if explicit:
        return explicit
    if settings is not None and hasattr(settings, "OPENAI_KEY_PASSPHRASE"):
        try:
            value = getattr(settings, "OPENAI_KEY_PASSPHRASE")
            if value:
                return str(value)
        except Exception:
            pass
    return os.getenv("OPENAI_KEY_PASSPHRASE")


def _ensure_openai_client(passphrase: Optional[str] = None) -> OpenAI:
    if os.getenv("OPENAI_API_KEY"):
        return OpenAI()

    pp = _get_passphrase(passphrase)
    if pp:
        manager = APIKeyManager()
        key = manager.get("openai", passphrase=pp)
        if key:
            return OpenAI(api_key=key)

    try:
        manager = APIKeyManager()
        key = manager.get("openai")
        if key:
            return OpenAI(api_key=key)
    except Exception:
        pass

    raise OpenAIError(
        "OpenAI API key not found. Set OPENAI_API_KEY env var or provide passphrase "
        "to unlock encrypted store via APIKeyManager."
    )


def _only_json(text: str) -> str:
    match = re.search(r"\[\s*{.*?}\s*\]", text, flags=re.S)
    if match:
        return match.group(0).strip()
    match = re.search(r'"items"\s*:\s*(\[\s*{.*?}\s*\])', text, flags=re.S)
    if match:
        return match.group(1).strip()
    return text.strip()


def _prepare_candidates(candidates: Sequence[Mapping[str, Any]]) -> list[PreparedCandidate]:
    prepared: list[PreparedCandidate] = []
    for index, candidate in enumerate(candidates):
        candidate_id = str(candidate.get("id", f"cand-{index + 1}"))
        name = str(candidate.get("name", candidate_id))
        raw_text = candidate.get("text")
        text = str(raw_text).strip() if raw_text is not None else ""
        prepared.append(
            PreparedCandidate(
                index=index,
                candidate_id=candidate_id,
                name=name,
                text=text,
            )
        )
    return prepared


def _compose_candidate_blob(prepared: Sequence[PreparedCandidate]) -> str:
    blocks: list[str] = []
    for cand in prepared:
        blocks.append(f"### [{cand.index}] {cand.name} ({cand.candidate_id})\n{cand.text}")
    return "\n\n".join(blocks)


def _coerce_int(value: Any, default: int = 0, *, minimum: Optional[int] = None, maximum: Optional[int] = None) -> int:
    if value is None:
        result = default
    else:
        try:
            result = int(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            result = default
    if minimum is not None and result < minimum:
        result = minimum
    if maximum is not None and result > maximum:
        result = maximum
    return result


def _extract_mapping_list(payload: object) -> list[Mapping[str, Any]]:
    mappings: list[Mapping[str, Any]] = []
    if isinstance(payload, list):
        payload_list = cast(list[object], payload)
        for entry in payload_list:
            if isinstance(entry, Mapping):
                mappings.append(cast(Mapping[str, Any], entry))
        return mappings
    if isinstance(payload, Mapping):
        mapping_payload = cast(Mapping[str, Any], payload)
        maybe_items = mapping_payload.get("items")
        if isinstance(maybe_items, list):
            items_list = cast(list[object], maybe_items)
            for entry in items_list:
                if isinstance(entry, Mapping):
                    mappings.append(cast(Mapping[str, Any], entry))
    return mappings


def _hydrate_rankings(
    payload: object,
    *,
    candidates: Sequence[PreparedCandidate],
) -> list[RankedCandidate]:
    normalized: list[RankedCandidate] = []
    for item in _extract_mapping_list(payload):
        idx = _coerce_int(item.get("index"), default=-1, minimum=0, maximum=len(candidates) - 1)
        if not (0 <= idx < len(candidates)):
            continue
        candidate = candidates[idx]
        score = _coerce_int(item.get("score"), default=0, minimum=0, maximum=100)
        raw_reason = item.get("reasons")
        reasons = str(raw_reason).strip() if raw_reason is not None else ""
        normalized.append(
            RankedCandidate(
                index=idx,
                candidate_id=candidate.candidate_id,
                name=candidate.name,
                score=score,
                reasons=reasons,
            )
        )
    return normalized


def _fallback_rankings(candidates: Sequence[PreparedCandidate], vacancy_text: str) -> list[RankedCandidate]:
    token_pattern = r"[A-Za-zА-Яа-я0-9_+.#-]{2,}"
    vocabulary = {
        token.lower()
        for token in re.findall(token_pattern, vacancy_text or "", flags=re.U)
    }

    def overlap_score(text: str) -> int:
        if not vocabulary:
            return 0
        words = {token.lower() for token in re.findall(token_pattern, text, flags=re.U)}
        intersection = len(vocabulary & words)
        return _coerce_int(100 * intersection / (len(vocabulary) + 1), default=0, minimum=0, maximum=100)

    def length_score(text: str) -> int:
        word_count = len(re.findall(r"\w{2,}", text, flags=re.U))
        return _coerce_int(15 + word_count // 15, default=0, minimum=0, maximum=100)

    ranked: list[RankedCandidate] = []
    for candidate in candidates:
        score = int(round(0.6 * overlap_score(candidate.text) + 0.4 * length_score(candidate.text)))
        ranked.append(
            RankedCandidate(
                index=candidate.index,
                candidate_id=candidate.candidate_id,
                name=candidate.name,
                score=_coerce_int(score, default=0, minimum=0, maximum=100),
                reasons="Fallback: keyword overlap + length heuristic.",
            )
        )
    ranked.sort(key=lambda item: item.score, reverse=True)
    return ranked


def _apply_top_k(items: Sequence[RankedCandidate], top_k: int | None) -> list[RankedCandidate]:
    if not top_k or top_k <= 0:
        return list(items)
    return list(items[:top_k])


def rank_candidates(
    vacancy_text: str,
    candidates: Sequence[Mapping[str, Any]],
    *,
    top_k: int = 5,
    model: str = "gpt-4o-mini",
    temperature: float = 0.2,
    weights: Optional[Mapping[str, float]] = None,
    passphrase: Optional[str] = None,
) -> list[dict[str, Any]]:
    if not candidates:
        return []

    prepared = _prepare_candidates(candidates)
    weights_payload: Mapping[str, float] = weights or _DEFAULT_WEIGHTS

    client = _ensure_openai_client(passphrase)

    system_msg = (
        "You are an experienced technical recruiter. Rank candidates for a vacancy. "
        "Consider skill relevance, recency of experience, communication clarity, and culture fit. "
        "Score each candidate from 0 to 100.\n"
        "Bias controls: do NOT over-reward extremely long careers; penalize outdated stacks; "
        "allow promising near-misses if other signals are strong.\n"
        "Output strictly a JSON array of objects with fields: "
        '{"index": <int>, "score": <int>, "reasons": "<short justification>"} '
        "(index is the order provided). No extra text."
    )

    user_msg = (
        f"VACANCY:\n{vacancy_text.strip()}\n\n"
        f"WEIGHTS: {json.dumps(dict(weights_payload))}\n\n"
        f"CANDIDATES:\n{_compose_candidate_blob(prepared)}\n\n"
        "Return top candidates with balanced judgment according to the weights."
    )

    response = client.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
    )

    content = (response.choices[0].message.content or "").strip()
    payload = _only_json(content)

    hydrated: list[RankedCandidate] = []
    try:
        parsed: object = json.loads(payload)
        hydrated = _hydrate_rankings(parsed, candidates=prepared)
    except Exception:
        hydrated = []

    if not hydrated:
        hydrated = _fallback_rankings(prepared, vacancy_text)

    hydrated.sort(key=lambda item: item.score, reverse=True)
    limited = _apply_top_k(hydrated, top_k)

    return [
        {
            "index": item.index,
            "id": item.candidate_id,
            "name": item.name,
            "score": item.score,
            "reasons": item.reasons,
        }
        for item in limited
    ]