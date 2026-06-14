"""Mikrofon va ovoz tanish diagnostikasi.

Ishlatish:
  .venv\\Scripts\\python.exe diagnose.py

5 soniya davomida gapiring (masalan enrollment jumlasini o'qing). Skript:
  - mikrofon qurilmasini va chastotasini ko'rsatadi,
  - ovoz darajasini (RMS) o'lchaydi (mikrofon ishlayaptimi?),
  - Vosk nima eshitganini va speaker x-vector chiqqanini ko'rsatadi.
"""

import time

import numpy as np
import sounddevice as sd

from aria.asr import Microphone, Recognizer
from aria.paths import ASR_MODEL_DIR, SPK_MODEL_DIR


def main() -> int:
    print("=== Audio qurilmalari ===")
    try:
        print(sd.query_devices())
        default_in = sd.query_devices(kind="input")
        print(f"\nDefault INPUT: {default_in['name']} "
              f"({int(default_in['default_samplerate'])} Hz)")
    except Exception as exc:
        print("Qurilmalarni o'qishda xato:", exc)
        return 1

    if not (ASR_MODEL_DIR.exists() and SPK_MODEL_DIR.exists()):
        print("\nModellar yo'q. Avval: py download_models.py")
        return 1

    from vosk import SetLogLevel
    SetLogLevel(-1)
    print("\nModellar yuklanmoqda...")
    rec = Recognizer(str(ASR_MODEL_DIR), str(SPK_MODEL_DIR), use_grammar=False)

    print("\n>>> HOZIR 5 SONIYA GAPIRING (jumlani baland o'qing)...\n")
    mic = Microphone()
    chunks = []
    spk = None
    texts = []
    try:
        mic.start()
        print(f"Mikrofon ochildi (tabiiy chastota: {mic._native_rate} Hz)")
        t0 = time.monotonic()
        while time.monotonic() - t0 < 5.0:
            data = mic.read(timeout=0.5)
            if not data:
                continue
            chunks.append(data)
            utt = rec.accept(data)
            if utt:
                if utt.text:
                    texts.append(utt.text)
                if utt.spk:
                    spk = utt.spk
        tail = rec.final()
        if tail:
            if tail.text:
                texts.append(tail.text)
            if tail.spk:
                spk = tail.spk
    finally:
        mic.stop()

    raw = b"".join(chunks)
    if raw:
        arr = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
        rms = float(np.sqrt(np.mean(arr ** 2)))
        peak = int(np.max(np.abs(arr))) if arr.size else 0
    else:
        rms = peak = 0

    print("\n=== Natija ===")
    print(f"Olingan audio: {len(raw)} bayt")
    print(f"Ovoz darajasi  RMS={rms:.0f}  peak={peak} (16-bit, max 32767)")
    if rms < 100:
        print("  ⚠️  Ovoz juda past/yo'q — mikrofon eshitmayapti yoki noto'g'ri qurilma.")
        print("     Windows > Settings > Privacy > Microphone'ni va default qurilmani tekshiring.")
    else:
        print("  ✅ Mikrofon ovoz olyapti.")
    print(f"Vosk eshitgani: {' | '.join(texts) if texts else '(hech narsa)'}")
    print(f"Speaker x-vector: {'OK, uzunlik ' + str(len(spk)) if spk else 'CHIQMADI'}")

    if rms >= 100 and spk:
        print("\n✅ Hammasi joyida — enrollment ishlashi kerak.")
    elif rms >= 100 and not spk:
        print("\n⚠️  Ovoz bor, lekin x-vector chiqmadi — uzunroq/balandroq gapiring.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
