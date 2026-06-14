"""Offline ovozli javob (Jarvis effekti) — Windows SAPI orqali, pyttsx3 bilan.

Javoblar inglizcha (buyruqlar ham inglizcha). Internet kerak emas.
TTS init yoki gapirish alohida thread'da, sekretsiz; xato bo'lsa jim qoladi.
"""

import threading


class Speaker:
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._lock = threading.Lock()
        self._engine = None
        if enabled:
            self._init_engine()

    def _init_engine(self) -> None:
        try:
            import pyttsx3
            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", 175)
        except Exception:
            self._engine = None  # TTS bo'lmasa ham app ishlayveradi

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        if enabled and self._engine is None:
            self._init_engine()

    def say(self, text: str) -> None:
        """Matnni ovoz bilan aytadi (bloklamaslik uchun alohida thread'da)."""
        if not self.enabled or self._engine is None:
            return
        threading.Thread(target=self._say_blocking, args=(text,), daemon=True).start()

    def _say_blocking(self, text: str) -> None:
        # Bitta vaqtda bitta gap (SAPI run-loop qayta kirishni yoqtirmaydi)
        with self._lock:
            try:
                self._engine.say(text)
                self._engine.runAndWait()
            except Exception:
                pass
