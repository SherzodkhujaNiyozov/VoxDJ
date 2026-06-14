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
                if callable(msg):
                    # Tk thread'ida bajariladigan topshiriq (masalan, matn kiritish oynasi)
                    try:
                        msg()
                    except Exception:
                        pass
                    continue
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

    def ask_text(self, title: str, prompt: str, initial: str = "",
                 timeout: float = 120.0):
        """Matn kiritish oynasi — overlay'ning MAVJUD Tk thread'ida quriladi.

        DIQQAT: Tkinter bir process'da faqat bitta thread'da ishonchli ishlaydi.
        Boshqa thread'da yangi tk.Tk() ochilsa, oyna klaviatura input'ini ololmaydi
        (wake so'zini yoza olmaslik shu sabab edi). Shuning uchun dialogni shu yerda
        — Tk thread'ida — quramiz va chaqiruvchi thread natija kelguncha bloklanadi.
        Bekor qilinsa yoki vaqt tugasa None qaytadi.
        """
        if self._root is None:
            return None
        result = {"value": None}
        done = threading.Event()
        self._q.put(lambda: self._build_input(title, prompt, initial, result, done))
        done.wait(timeout)
        return result["value"]

    def _build_input(self, title, prompt, initial, result, done):
        import tkinter as tk
        try:
            dlg = tk.Toplevel(self._root)
        except Exception:
            done.set()
            return
        dlg.title(title)
        dlg.attributes("-topmost", True)
        dlg.resizable(False, False)
        tk.Label(dlg, text=prompt, font=("Segoe UI", 10),
                 padx=18, pady=(16, 6)).pack(anchor="w")
        var = tk.StringVar(value=initial)
        entry = tk.Entry(dlg, textvariable=var, font=("Segoe UI", 13), width=26)
        entry.pack(padx=18, pady=(0, 4))
        entry.icursor("end")
        entry.select_range(0, "end")

        def finish(value):
            result["value"] = value
            try:
                dlg.destroy()
            finally:
                done.set()

        btns = tk.Frame(dlg)
        btns.pack(padx=18, pady=14)
        tk.Button(btns, text="OK", width=9,
                  command=lambda: finish(var.get().strip())).pack(side="left", padx=6)
        tk.Button(btns, text="✕", width=4,
                  command=lambda: finish(None)).pack(side="left", padx=6)
        dlg.bind("<Return>", lambda e: finish(var.get().strip()))
        dlg.bind("<Escape>", lambda e: finish(None))
        dlg.protocol("WM_DELETE_WINDOW", lambda: finish(None))

        dlg.update_idletasks()
        w, h = dlg.winfo_width(), dlg.winfo_height()
        sw, sh = dlg.winfo_screenwidth(), dlg.winfo_screenheight()
        dlg.geometry(f"+{(sw - w) // 2}+{(sh - h) // 3}")
        dlg.lift()
        dlg.focus_force()
        entry.focus_force()

    def stop(self):
        self._q.put(None)
