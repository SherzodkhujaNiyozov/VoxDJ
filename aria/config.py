"""Sozlamalar: JSON faylga atomik yozish + qiymatlarni clamp qilish.

Database yo'q — oddiy JSON. Buzilgan fayl bo'lsa, default'larga qaytadi.
"""

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field, fields

from .paths import CONFIG_PATH, ensure_appdata

SUPPORTED_LANGS = ("uz", "en", "es", "ja", "ru")


@dataclass
class Config:
    # UI tili (buyruqlar har doim inglizcha; bu faqat interfeys uchun)
    language: str = "en"
    # True bo'lsa — istalgan odam boshqara oladi; False — faqat egasi (default)
    allow_all_users: bool = False
    # "aria" uyg'otish so'zi talab qilinsinmi (tasodifiy buyruqlardan himoya)
    wake_word_enabled: bool = True
    # Ovozli javob (Jarvis effekti)
    voice_feedback: bool = True
    # Ekran burchagidagi vizual bildirishnoma (ovoz o'chiq bo'lsa ham ko'rinadi)
    overlay_enabled: bool = True
    # Windows bilan birga ishga tushsinmi
    autostart: bool = False
    # Speaker tasdiqlash chegarasi (cosine similarity). Past = ko'proq qabul qiladi.
    speaker_threshold: float = 0.45
    # Nisbiy ovoz qadami ("louder"/"quieter") foizda
    volume_step: int = 10

    def clamp(self) -> "Config":
        """Qiymatlarni xavfsiz oraliqqa keltiradi."""
        if self.language not in SUPPORTED_LANGS:
            self.language = "en"
        self.speaker_threshold = _clampf(self.speaker_threshold, 0.20, 0.90)
        self.volume_step = int(_clampf(self.volume_step, 1, 50))
        self.allow_all_users = bool(self.allow_all_users)
        self.wake_word_enabled = bool(self.wake_word_enabled)
        self.voice_feedback = bool(self.voice_feedback)
        self.overlay_enabled = bool(self.overlay_enabled)
        self.autostart = bool(self.autostart)
        return self


def _clampf(value, lo, hi):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return lo
    return max(lo, min(hi, value))


def load() -> Config:
    """Configni o'qiydi; fayl yo'q yoki buzilgan bo'lsa default qaytaradi."""
    try:
        raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return Config()
    known = {f.name for f in fields(Config)}
    clean = {k: v for k, v in raw.items() if k in known}
    return Config(**clean).clamp()


def save(cfg: Config) -> None:
    """Atomik yozish: temp faylga yozib, keyin o'rniga qo'yadi (yarim yozilmaydi)."""
    ensure_appdata()
    cfg.clamp()
    data = json.dumps(asdict(cfg), indent=2, ensure_ascii=False)
    fd, tmp = tempfile.mkstemp(dir=str(CONFIG_PATH.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, CONFIG_PATH)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
