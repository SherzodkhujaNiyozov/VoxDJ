"""Vosk modellarini bir marta yuklab oladi (internet faqat shu yerda kerak).

Ikki model:
  - vosk-model-small-en-us-0.15  (nutqni tanish, ~40 MB)
  - vosk-model-spk-0.4           (speaker x-vector, ~13 MB)

Ishlatish:  py download_models.py
Modellar  models/  papkasiga chiqariladi (repoga kirmaydi — .gitignore'da).

Xavfsizlik: yuklab bo'lgach SHA-256 chop etiladi. EXPECTED_SHA256 ga qiymat
qo'ysangiz, mosligi tekshiriladi (pinning).
"""

import hashlib
import sys
import urllib.request
import zipfile
from pathlib import Path

MODELS_DIR = Path(__file__).resolve().parent / "models"

MODELS = [
    {
        "name": "vosk-model-small-en-us-0.15",
        "url": "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip",
        "sha256": None,  # ixtiyoriy pinning — yuklab olgach chop etilgan qiymatni qo'ying
    },
    {
        "name": "vosk-model-spk-0.4",
        "url": "https://alphacephei.com/vosk/models/vosk-model-spk-0.4.zip",
        "sha256": None,
    },
]


def _download(url: str, dest: Path) -> None:
    print(f"  yuklanmoqda: {url}")
    last = [-1]

    def hook(block, block_size, total):
        if total > 0:
            pct = min(100, block * block_size * 100 // total)
            if pct != last[0]:  # faqat foiz o'zgarganda chizamiz
                last[0] = pct
                sys.stdout.write(f"\r  {pct:3d}%")
                sys.stdout.flush()

    urllib.request.urlretrieve(url, dest, reporthook=hook)
    print()


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _safe_extract(zf: zipfile.ZipFile, dest: Path) -> None:
    """Zip-slip himoyasi bilan arxivni ochadi.

    Zararli (yoki buzilgan) arxiv a'zo nomida "../" yoki absolyut yo'l orqali
    dest papkasidan TASHQARIGA fayl yozishi mumkin. Har bir a'zo dest ichida
    qolishini tekshiramiz, aks holda to'xtaymiz.
    """
    dest = dest.resolve()
    for member in zf.namelist():
        target = (dest / member).resolve()
        if target != dest and not target.is_relative_to(dest):
            raise RuntimeError(f"Xavfli arxiv a'zosi (zip-slip): {member!r}")
    zf.extractall(dest)


def main() -> int:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    for m in MODELS:
        target = MODELS_DIR / m["name"]
        if target.exists():
            print(f"[skip] {m['name']} allaqachon bor")
            continue
        if not m["url"].lower().startswith("https://"):
            print(f"  XATO: faqat HTTPS manzillar qo'llab-quvvatlanadi: {m['url']}")
            return 1
        print(f"[get ] {m['name']}")
        zip_path = MODELS_DIR / (m["name"] + ".zip")
        _download(m["url"], zip_path)

        digest = _sha256(zip_path)
        print(f"  SHA-256: {digest}")
        if m["sha256"] and digest != m["sha256"]:
            print("  XATO: SHA-256 mos kelmadi! Yuklash buzilgan bo'lishi mumkin.")
            zip_path.unlink(missing_ok=True)
            return 1

        with zipfile.ZipFile(zip_path) as zf:
            _safe_extract(zf, MODELS_DIR)
        zip_path.unlink(missing_ok=True)

        if not target.exists():
            print(f"  XATO: {target} chiqmadi — arxiv tuzilishi kutilganidan farq qiladi.")
            return 1
        print(f"  OK -> {target}")

    print("\nTayyor. Endi:  py -m aria")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
