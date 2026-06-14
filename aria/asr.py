"""Offline nutqni tanish (Vosk) + speaker x-vector.

Bitta Vosk pipeline: cheklangan grammatika (faqat buyruq so'zlari) → qisqa
inglizcha buyruqlar uchun yuqori aniqlik; har bir gap oxirida 128-o'lchamli
x-vector (kim gapirgani) ham qaytadi.
"""

import json
import queue
from dataclasses import dataclass
from typing import List, Optional

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000
BLOCK_SIZE = 8000  # ~0.5s bloklar

# Uyg'otish so'zisiz buyruq lug'ati (doimiy qism).
# Eslatmalar:
#   - "audio" olib tashlandi: "aria" wake bilan akustik to'qnashar (4/6 fail).
#   - "unmute" OOV — "only mute" bo'lib chiqadi (commands.py ushlaydi).
#   - "skip" — next uchun ("next"/"forward" ishonchsiz).
#   - "me"/"everyone" olib tashlandi: "one"ni o'g'irlardi.
#   - "everyone"/"private" — rejim almashtirish (3/2 bo'g'in — raqam bilan to'qnashmaydi).
#   - "microphone" — mic o'zgartirish buyrug'i.
_GRAMMAR_BASE = (
    "play pause stop skip next previous back "
    "mute only louder quieter volume sound up down percent "
    "spotify chrome firefox edge youtube telegram music app "
    "everyone private microphone "
    "zero one two three four five six seven eight nine ten "
    "eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen "
    "twenty thirty forty fifty sixty seventy eighty ninety hundred"
)


def build_grammar(wake_word: str = "aria", wake_alts: Optional[List[str]] = None) -> str:
    """Uyg'otish so'zi + fonetik variantlar + asosiy buyruq lug'ati."""
    if wake_alts is None:
        wake_alts = ["area"] if wake_word == "aria" else []
    parts = [wake_word] + [a for a in wake_alts if a and a != wake_word]
    return " ".join(parts) + " " + _GRAMMAR_BASE


@dataclass
class Utterance:
    text: str
    spk: Optional[list]  # x-vector (None bo'lishi mumkin — gap juda qisqa bo'lsa)


class Recognizer:
    """Vosk modeli + speaker modeli + grammatikali KaldiRecognizer."""

    def __init__(self, asr_model_dir: str, spk_model_dir: str,
                 wake_word: str = "aria", wake_alts: Optional[List[str]] = None,
                 use_grammar: bool = True):
        from vosk import KaldiRecognizer, Model, SpkModel

        self._KaldiRecognizer = KaldiRecognizer
        self._model = Model(asr_model_dir)
        self._spk_model = SpkModel(spk_model_dir)
        self._wake_word = wake_word
        self._wake_alts = wake_alts if wake_alts is not None \
            else (["area"] if wake_word == "aria" else [])
        self._grammar = build_grammar(wake_word, self._wake_alts)
        self._use_grammar = use_grammar
        self._rec = self._make_rec(use_grammar)

    def _make_rec(self, use_grammar: bool):
        if use_grammar:
            rec = self._KaldiRecognizer(
                self._model, SAMPLE_RATE, json.dumps([self._grammar, "[unk]"]))
        else:
            rec = self._KaldiRecognizer(self._model, SAMPLE_RATE)
        rec.SetSpkModel(self._spk_model)
        rec.SetWords(False)
        return rec

    def set_wake(self, word: str, alts: Optional[List[str]] = None) -> None:
        """Uyg'otish so'zini o'zgartiradi va grammatikani qayta quradi."""
        self._wake_word = word
        self._wake_alts = alts if alts is not None else (["area"] if word == "aria" else [])
        self._grammar = build_grammar(word, self._wake_alts)
        self._rec = self._make_rec(self._use_grammar)

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
