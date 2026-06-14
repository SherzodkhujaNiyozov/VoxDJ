"""Jonli buyruq diagnostikasi — model SIZNING ovozingizda nimani eshitishini ko'rsatadi.

Ishlatish:
  .venv\\Scripts\\python.exe listen_test.py

Keyin buyruqlarni ayting: "aria pause", "aria play", "aria skip", "aria volume five zero" ...
Har bir gap uchun: model NIMANI eshitdi + qaysi BUYRUQqa aylandi ko'rinadi.
To'xtatish: Ctrl+C.

Natijani nusxalab yuboring — shunda "pause" qaysi so'zga adashayotganini ko'rib,
aniq tuzatamiz.
"""

from vosk import SetLogLevel

from aria import commands as c
from aria.asr import Microphone, Recognizer
from aria.paths import ASR_MODEL_DIR, SPK_MODEL_DIR


def main() -> int:
    if not (ASR_MODEL_DIR.exists() and SPK_MODEL_DIR.exists()):
        print("Modellar yo'q. Avval: py download_models.py")
        return 1
    SetLogLevel(-1)
    print("Modellar yuklanmoqda...")
    rec = Recognizer(str(ASR_MODEL_DIR), str(SPK_MODEL_DIR))
    mic = Microphone()
    mic.start()
    print(f"\nMikrofon ochildi ({mic._native_rate} Hz). Buyruqlarni ayting.")
    print("Format:  EShITILDI  ->  BUYRUQ\n(to'xtatish: Ctrl+C)\n")
    try:
        while True:
            data = mic.read(timeout=0.3)
            if not data:
                continue
            utt = rec.accept(data)
            if utt and utt.text:
                had, rest = c.strip_wake(utt.text.split())
                cmd = c.parse(" ".join(rest))
                wake = "[wake] " if had else "        "
                print(f"  {wake}{utt.text!r:30} -> {cmd}")
    except KeyboardInterrupt:
        print("\nTo'xtatildi.")
    finally:
        mic.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
