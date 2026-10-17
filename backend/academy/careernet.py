import math
import re
from collections import Counter
from typing import Iterable

from .career_inference import infer_score, load_weights


class CareerNet:
    """A lightweight deep-learning-inspired recommender for career matching.

    The model keeps a deterministic token-overlap baseline for compatibility with
    the existing API, while the latency-sensitive inference step is isolated in a
    dedicated weights file and inference function. This keeps the app stable while
    enabling a more realistic model architecture for future ML upgrades.
    """

    @staticmethod
    def normalize(values: Iterable[str]) -> list[str]:
        tokens: list[str] = []
        for value in values or []:
            if not isinstance(value, str):
                continue
            cleaned = re.sub(r"[^a-z0-9]+", " ", value.lower().strip())
            tokens.extend(part for part in cleaned.split() if part)
        return tokens

    @staticmethod
    def _feature_vector(items: Iterable[str]) -> dict[str, float]:
        counts = Counter(CareerNet.normalize(items))
        if not counts:
            return {}
        total = sum(counts.values())
        return {
            token: (1.0 + math.log1p(count)) * (1.0 + math.log1p(total))
            for token, count in counts.items()
        }

    @staticmethod
    def _legacy_score(user_interests: Iterable[str], career_interests: Iterable[str]) -> float:
        user_tokens = {value.strip().lower() for value in user_interests or [] if isinstance(value, str)}
        career_tokens = [value.strip().lower() for value in career_interests or [] if isinstance(value, str)]
        if not career_tokens:
            return 0.0
        shared = {token for token in user_tokens if token in set(career_tokens)}
        if not shared and not user_tokens:
            return 0.0
        return float(math.floor(100 * len(shared) / max(1, len(career_tokens)) + 0.5))

    def score(self, user_interests: Iterable[str], career_interests: Iterable[str]) -> float:
        legacy_score = self._legacy_score(user_interests, career_interests)
        latent_score = infer_score(user_interests, career_interests, load_weights())
        blended = (0.8 * legacy_score) + (0.2 * latent_score)
        return float(max(0.0, min(100.0, blended)))

    def recommend(self, user_interests: Iterable[str], career_interests: Iterable[str]) -> float:
        return self.score(user_interests, career_interests)
