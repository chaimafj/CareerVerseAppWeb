import json
import math
import re
from pathlib import Path
from typing import Iterable

WEIGHTS_PATH = Path(__file__).resolve().parent / "weights" / "careernet_weights.json"


def normalize_interest(value: object) -> str:
    if not isinstance(value, str):
        return ""
    cleaned = re.sub(r"[^a-z0-9]+", " ", value.strip().lower())
    return " ".join(part for part in cleaned.split() if part)


def normalize_interests(values: Iterable[object] | None) -> list[str]:
    items: list[str] = []
    for value in values or []:
        normalized = normalize_interest(value)
        if normalized:
            items.append(normalized)
    return items


def _default_weights() -> dict:
    return {
        "embedding_dim": 8,
        "token_embedding": {
            "default": [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
        },
        "output_bias": 0.0,
    }


def load_weights(path: Path | str = WEIGHTS_PATH) -> dict:
    target = Path(path)
    if not target.exists():
        return _default_weights()
    try:
        with target.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict):
            return _default_weights()
        return payload
    except (json.JSONDecodeError, OSError):
        return _default_weights()


def _embedding_for_token(token: str, weights: dict) -> list[float]:
    token_embedding = weights.get("token_embedding", {})
    if isinstance(token_embedding, dict) and token in token_embedding:
        value = token_embedding[token]
        if isinstance(value, list) and value and all(isinstance(v, (int, float)) for v in value):
            return [float(v) for v in value]
    fallback = weights.get("token_embedding", {}).get("default")
    if isinstance(fallback, list) and fallback and all(isinstance(v, (int, float)) for v in fallback):
        return [float(v) for v in fallback]
    return [1.0] * int(weights.get("embedding_dim", 8))


def infer_score(user_interests: Iterable[object], career_interests: Iterable[object], weights: dict | None = None) -> float:
    user_items = normalize_interests(user_interests)
    career_items = normalize_interests(career_interests)
    if not career_items:
        return 0.0

    weights = weights or load_weights()
    user_set = set(user_items)
    career_set = set(career_items)
    overlap = sorted(user_set & career_set)

    candidate = overlap
    if not candidate:
        return 0.0

    interest_score = 100.0 * len(candidate) / max(1, len(career_set))
    token_vectors = [_embedding_for_token(token, weights) for token in candidate]
    latent_gain = 0.0
    if token_vectors:
        dim = len(token_vectors[0])
        combined = [0.0] * dim
        for vector in token_vectors:
            for index, value in enumerate(vector[:dim]):
                combined[index] += value
        latent_gain = sum(combined) / max(1, len(combined) * len(token_vectors))
    match_score = (0.6 * interest_score) + (0.4 * min(100.0, max(0.0, latent_gain * 100.0)))
    return math.floor(match_score + 0.5)
