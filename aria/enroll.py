"""Ovozni tanishtirish oynasi (birinchi ishga tushganda yoki qayta yozishda).

Tkinter oynasi: foydalanuvchi jumlani o'qiydi, biz bir necha soniya yozib,
speaker x-vectorlarini yig'amiz va voiceprint sifatida saqlaymiz.
"""

import threading
import tkinter as tk
from tkinter import ttk

from .asr import Microphone, Recognizer
from .i18n import I18n
from .speaker import Voiceprint

_CAPTURE_SECONDS = 6.0


def run_enrollment(recognizer: Recognizer, voiceprint: Voiceprint, i18n: I18n,
                   wake_word: str = "aria") -> bool:
    """Modal enrollment oynasini ochadi. Muvaffaqiyatli bo'lsa True qaytaradi.

    Tkinter main thread'da ishlashi kerak — shu funksiya main thread'dan chaqiriladi.
    """
    state = {"ok": False}
    wake_cap = wake_word.capitalize()

    root = tk.Tk()
    root.title(i18n.t("enroll_title"))
    root.geometry("520x320")
    root.resizable(False, False)
    root.eval("tk::PlaceWindow . center")

    frm = ttk.Frame(root, padding=24)
    frm.pack(fill="both", expand=True)

    ttk.Label(frm, text=wake_cap, font=("Segoe UI", 20, "bold")).pack(anchor="w")
    ttk.Label(frm, text=i18n.t("enroll_intro"), wraplength=470,
              justify="left").pack(anchor="w", pady=(8, 12))
    ttk.Label(frm, text=i18n.t("enroll_phrase", wake=wake_cap), wraplength=470,
              font=("Segoe UI", 11, "italic"),
              foreground="#2563eb").pack(anchor="w", pady=(0, 16))

    status = ttk.Label(frm, text="", font=("Segoe UI", 10))
    status.pack(anchor="w")

    btns = ttk.Frame(frm)
    btns.pack(side="bottom", fill="x", pady=(16, 0))
    start_btn = ttk.Button(btns, text=i18n.t("enroll_start"))
    start_btn.pack(side="right")
    close_btn = ttk.Button(btns, text=i18n.t("enroll_close"),
                           command=root.destroy)
    close_btn.pack(side="right", padx=(0, 8))

    def set_status(text: str) -> None:
        root.after(0, lambda: status.config(text=text))

    def capture_worker() -> None:
        import time
        mic = Microphone()
        samples = []
        try:
            # Enrollment: grammatikasiz — har qanday nutqdan x-vector olamiz
            recognizer.restart(use_grammar=False)
            mic.start()
            set_status(i18n.t("enroll_listening"))
            t0 = time.monotonic()
            while time.monotonic() - t0 < _CAPTURE_SECONDS:
                data = mic.read(timeout=0.5)
                if not data:
                    continue
                utt = recognizer.accept(data)
                if utt and utt.spk:
                    samples.append(utt.spk)
                    set_status(i18n.t("enroll_progress", n=len(samples), total=3))
            tail = recognizer.final()
            if tail and tail.spk:
                samples.append(tail.spk)
        except Exception as exc:
            import traceback
            print("[enroll] xato:", exc)
            traceback.print_exc()
            samples = []
        finally:
            mic.stop()
            recognizer.restart(use_grammar=True)  # tinglash uchun grammatikani qaytaramiz

        if samples:
            voiceprint.save_from_samples(samples)
            state["ok"] = True
            set_status(i18n.t("enroll_success"))
            root.after(0, lambda: start_btn.config(state="disabled"))
            root.after(1200, root.destroy)
        else:
            set_status(i18n.t("enroll_failed"))
            root.after(0, lambda: start_btn.config(
                state="normal", text=i18n.t("enroll_retry")))

    def on_start() -> None:
        start_btn.config(state="disabled")
        threading.Thread(target=capture_worker, daemon=True).start()

    start_btn.config(command=on_start)
    root.mainloop()
    return state["ok"]
