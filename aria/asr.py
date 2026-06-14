"""Offline nutqni tanish (Vosk) + speaker x-vector.

Bitta Vosk pipeline: cheklangan grammatika (faqat buyruq so'zlari) → qisqa
inglizcha buyruqlar uchun yuqori aniqlik; har bir gap oxirida 128-o'lchamli
x-vector (kim gapirgani) ham qaytadi.
"""

import json
import queue
from dataclasses import dataclass
from typing import Optional

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000
BLOCK_SIZE = 8000  # ~0.5s bloklar

# Cheklangan lug'at — Vosk shulardan tashqari so'zlarni tanimaydi (aniqlik oshadi).
# "aria/area" — uyg'otish so'zi va uning fonetik varianti.
# Test bilan tanlangan ishonchli lug'at (kichik en model):
#   - "aria" — wake (yakka holda ham aniq tanildi); "area" — fonetik zaxira
#   - "skip" — next uchun ("next"/"forward" ishonchsiz; "forward" "four"ni o'g'irlaydi)
#   - "unmute" modelda YO'Q — "only mute" bo'lib chiqadi (commands.py ushlaydi)
#   - raqamlar raqamma-raqam: "five zero" = 50
#   - "me"/"everyone" qo'shilmadi: ular "one"ni o'g'irlaydi. Rejim almashtirish
#     (faqat egasi / hamma) tray checkbox orqali. "only" faqat unmute uchun qoldi.
GRAMMAR_WORDS = (
    "aria area "
    "play pause stop skip next previous back "
    # "audio" OLIB TASHLANDI: u wake "aria"ni o'g'irlardi (model chalkashtirardi).
    # Ovoz uchun "volume" ishlatiladi.
    "mute only louder quieter volume sound up down percent "
    "spotify chrome firefox edge youtube telegram music app "
    "zero one two three four five six seven eight nine ten "
    "eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen "
    "twenty thirty forty fifty sixty seventy eighty ninety hundred"
)


@dataclass
class Utterance:
    text: str
    spk: Optional[list]  # x-vector (None bo'lishi mumkin — gap juda qisqa bo'lsa)


class Recognizer:
    """Vosk modeli + speaker modeli + grammatikali KaldiRecognizer."""

    def __init__(self, asr_model_dir: str, spk_model_dir: str, use_grammar: bool = True):
        from vosk import KaldiRecognizer, Model, SpkModel

        self._KaldiRecognizer = KaldiRecognizer
        self._model = Model(asr_model_dir)
        self._spk_model = SpkModel(spk_model_dir)
        self._use_grammar = use_grammar
        self._rec = self._make_rec(use_grammar)

    def _make_rec(self, use_grammar: bool):
        if use_grammar:
            rec = self._KaldiRecognizer(
                self._model, SAMPLE_RATE, json.dumps([GRAMMAR_WORDS, "[unk]"]))
        else:
            rec = self._KaldiRecognizer(self._model, SAMPLE_RATE)
        rec.SetSpkModel(self._spk_model)
        rec.SetWords(False)
        return rec

    def restart(self, use_grammar: Optional[bool] = None) -> None:
        """Holatni tozalab, yangi KaldiRecognizer quradi (grammatikani almashtirish mumkin).

        Enrollment uchun grammatikasiz (use_grammar=False) ishlatiladi — har qanday
        nutqdan x-vector olinadi, hatto buyruq so'zlari bo'lmasa ham.
        """
        if use_grammar is None:
            use_grammar = self._use_grammar
        self._use_grammar = use_grammar
        self._rec = self._make_rec(use_grammar)

    def accept(self, data: bytes) -> Optional[Utterance]:
        """Audio blokini yuboradi. Gap tugaganda Utterance, aks holda None.

        Diqqat: matn bo'sh bo'lsa ham Utterance qaytadi (spk vektor bo'lishi mumkin) —
        chaqiruvchi o'zi text/spk bo'yicha qaror qiladi.
        """
        if self._rec.AcceptWaveform(data):
            res = json.loads(self._rec.Result())
            return Utterance(text=res.get("text", "").strip(), spk=res.get("spk"))
        return None

    def final(self) -> Optional[Utterance]:
        """Oqim to'xtaganda qolgan natijani oladi (matn bo'sh bo'lsa ham qaytadi)."""
        res = json.loads(self._rec.FinalResult())
        return Utterance(text=res.get("text", "").strip(), spk=res.get("spk"))


class Microphone:
    """Mikrofon oqimi → 16kHz mono int16 bytes navbati.

    Qurilmaning TABIIY chastotasida ochiladi (ko'p mikrofonlar 16000'ni qo'llamaydi —
    odatda 44100/48000), so'ng numpy bilan 16000'ga resample qilinadi. Bu "jim oqim"
    yoki "oqim ochilmadi" muammosining oldini oladi.
    """

    def __init__(self, device=None):
        self._q: "queue.Queue[bytes]" = queue.Queue()
        self._stream: Optional[sd.InputStream] = None
        self._device = device
        self._native_rate = SAMPLE_RATE

    def _callback(self, indata, frames, time_info, status):
        # indata: int16 (frames, channels) — birinchi kanalni olamiz
        mono = indata[:, 0].astype(np.float32)
        if self._native_rate != SAMPLE_RATE:
            n = max(1, int(round(len(mono) * SAMPLE_RATE / self._native_rate)))
            x = np.linspace(0.0, 1.0, len(mono), endpoint=False)
            xi = np.linspace(0.0, 1.0, n, endpoint=False)
            mono = np.interp(xi, x, mono)
        self._q.put(mono.astype(np.int16).tobytes())

    def start(self) -> None:
        info = sd.query_devices(self._device, "input")
        self._native_rate = int(info["default_samplerate"]) or SAMPLE_RATE
        blocksize = int(self._native_rate * 0.5)  # ~0.5s bloklar
        self._stream = sd.InputStream(
            samplerate=self._native_rate,
            blocksize=blocksize,
            device=self._device,
            dtype="int16",
            channels=1,
            callback=self._callback,
        )
        self._stream.start()

    def read(self, timeout: float = 0.5) -> Optional[bytes]:
        try:
            return self._q.get(timeout=timeout)
        except queue.Empty:
            return None

    def stop(self) -> None:
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
