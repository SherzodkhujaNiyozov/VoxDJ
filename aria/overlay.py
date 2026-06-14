"""Ekran burchagida kichik bildirishnoma (buyruq qabul qilinganda ko'rinadi).

Ayniqsa ovoz o'chirilgan paytda foydali — eshitilmaydigan ovozli javob o'rniga
vizual tasdiq beradi. Tkinter o'z thread'ida ishlaydi; show() istalgan thread'dan
xavfsiz chaqiriladi (xabar navbat orqali Tk thread'iga uzatiladi).
"""

import queue
import threading


class Overlay:
    def __init__(self, enabled: bool = True, duration: float = 1.5):
        self.enabled = enabled
        self._duration = duration
        self._q: "queue.Queue" = queue.Queue()
        self._root = None
        self._win = None
        self._label = None
        self._hide_id = None
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    # ---- Tk thread ----
    def _run(self):
        import tkinter as tk
        try:
            self._root = tk.Tk()
        except Exception:
            return  # GUI bo'lmasa, overlay'siz ham app ishlayveradi
        root = self._root
        root.withdraw()

        win = tk.Toplevel(root)
        self._win = win
        win.overrideredirect(True)          # ramka/sarlavhasiz
        win.attributes("-topmost", True)
        try:
            win.attributes("-alpha", 0.93)
        except Exception:
            pass
        frame = tk.Frame(win, bg="#1e293b", highlightthickness=0)
        frame.pack(fill="both", expand=True)
        self._label = tk.Label(
            frame, text="", bg="#1e293b", fg="#f1f5f9",
            font=("Segoe UI", 13, "bold"), padx=24, pady=14,
        )
        self._label.pack()
        win.withdraw()

        self._poll()
        root.mainloop()

    def _poll(self):
        try:
            while True:
                msg = self._q.get_nowait()
                if msg is None:
                    self._root.quit()
                    return
                self._display(msg)
        except queue.Empty:
            pass
        self._root.after(60, self._poll)

    def _display(self, text: str):
        win = self._win
        self._label.config(text=text)
        win.deiconify()
        win.update_idletasks()
        w, h = win.winfo_width(), win.winfo_height()
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        x, y = sw - w - 30, sh - h - 70   # pastki-o'ng burchak (taskbar tepasida)
        win.geometry(f"+{x}+{y}")
        win.lift()
        if self._hide_id:
            self._root.after_cancel(self._hide_id)
        self._hide_id = self._root.after(int(self._duration * 1000), win.withdraw)

    # ---- Istalgan thread'dan ----
    def show(self, text: str):
        if self.enabled and text:
            self._q.put(text)

    def set_enabled(self, enabled: bool):
        self.enabled = enabled

    def stop(self):
        self._q.put(None)
