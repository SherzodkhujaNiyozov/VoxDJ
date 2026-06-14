"""Ovoz biometriyasi: egasining "ovoz barmoq izi"ni saqlash va tasdiqlash.

Vosk speaker modeli har bir gapdan 128 o'lchamli x-vector beradi. Egasining
o'rtacha (normallashtirilgan) vektorini lokal JSON faylga saqlaymiz va keyingi
buyruqlarni cosine similarity orqali solishtiramiz. Database emas — bitta fayl.
"""

import json
from typing import Optional

import numpy as np

from .paths import VOICEPRINT_PATH, ensure_appdata


def _normalize(vec: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vec)
    return vec / norm if norm > 1e-9 else vec


def cosine_similarity(a, b) -> float:
    a = _normalize(np.asarray(a, dtype=np.float64))
    b = _normalize(np.asarray(b, dtype=np.float64))
    return float(np.dot(a, b))


class Voiceprint:
    """Egasining ovoz izi (lokal faylda)."""

    def __init__(self):
        self.embedding: Optional[np.ndarray] = None
        self.load()

    def exists(self) -> bool:
        return self.embedding is not None

    def load(self) -> None:
        try:
            data = json.loads(VOICEPRINT_PATH.read_text(encoding="utf-8"))
            emb = np.asarray(data["embedding"], dtype=np.float64)
            self.embedding = _normalize(emb) if emb.size else None
        except (OSError, json.JSONDecodeError, KeyError, ValueError):
            self.embedding = None

    def save_from_samples(self, samples: list) -> None:
        """Bir nechta x-vectorlarning o'rtachasini ish izi sifatida saqlaydi."""
        if not samples:
            raise ValueError("Bo'sh namuna ro'yxati")
        mean = np.mean(np.asarray(samples, dtype=np.float64), axis=0)
        self.embedding = _normalize(mean)
        ensure_appdata()
        VOICEPRINT_PATH.write_text(
            json.dumps({"version": 1, "embedding": self.embedding.tolist()}),
            encoding="utf-8",
        )

    def verify(self, vec, threshold: float) -> bool:
        """Kelgan x-vector egasiga tegishlimi? (cosine >= threshold)"""
        if self.embedding is None or vec is None:
            return False
        return cosine_similarity(self.embedding, vec) >= threshold

    def similarity(self, vec) -> float:
        if self.embedding is None or vec is None:
            return 0.0
        return cosine_similarity(self.embedding, vec)
