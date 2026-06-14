"""Lokal fayl yo'llari. Hech narsa repoda yoki database'da emas —
foydalanuvchi ma'lumotlari %APPDATA%/Aria da, modellar esa proekt yonidagi models/ da."""

import os
from pathlib import Path

from . import APP_NAME

# %APPDATA%/Aria — config va voiceprint shu yerda (offline, lokal)
APPDATA_DIR = Path(os.environ.get("APPDATA", str(Path.home()))) / APP_NAME
CONFIG_PATH = APPDATA_DIR / "config.json"
VOICEPRINT_PATH = APPDATA_DIR / "voiceprint.json"

# Proekt ildizi (.../Aria) va modellar papkasi
PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = PROJECT_ROOT / "models"

# Vosk modellari (download_models.py yuklab oladi)
ASR_MODEL_DIR = MODELS_DIR / "vosk-model-small-en-us-0.15"
SPK_MODEL_DIR = MODELS_DIR / "vosk-model-spk-0.4"


def ensure_appdata() -> None:
    """%APPDATA%/Aria papkasini yaratadi (mavjud bo'lsa, hech narsa qilmaydi)."""
    APPDATA_DIR.mkdir(parents=True, exist_ok=True)
