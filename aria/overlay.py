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

    def ask_text(self, title: str, prompt: str, initial: str, on_submit):
        """Matn kiritish oynasini ochadi — ASINXRON, hech qaysi thread'ni bloklamaydi.

        Oyna overlay'ning MAVJUD Tk thread'ida quriladi (Tkinter bir process'da
        bitta thread'da ishlashi shart — boshqa thread'da yangi tk.Tk() ochilsa
        klaviatura input ololmaydi). Foydalanuvchi tasdiqlaganda yoki bekor
        qilganda `on_submit(value)` Tk thread'ida chaqiriladi (bekor → None).

        Chaqiruvchi (masalan tray callback) darhol qaytadi — shuning uchun tray
        muzlab qolmaydi.
        """
        if self._root is None:
            on_submit(None)
            return
        self._q.put(lambda: self._build_input(title, prompt, initial, on_submit))

    def _build_input(self, title, prompt, initial, on_submit):
        import tkinter as tk
        import traceback
        W, H = 420, 180
        try:
            dlg = tk.Toplevel(self._root)
            dlg.title(title)
            dlg.configure(bg="#1e293b")
            dlg.resizable(False, False)
            dlg.attributes("-topmost", True)

            wrap = tk.Frame(dlg, bg="#1e293b")
            wrap.pack(fill="both", expand=True, padx=22, pady=20)
            tk.Label(wrap, text=prompt, bg="#1e293b", fg="#f1f5f9",
                     font=("Segoe UI", 11)).pack(anchor="w")
            var = tk.StringVar(value=initial or "")
            entry = tk.Entry(wrap, textvariable=var, font=("Segoe UI", 14),
                             relief="flat", bg="#f8fafc", fg="#0f172a",
                             insertbackground="#0f172a")
            entry.pack(fill="x", pady=(12, 0), ipady=7)

            guard = {"done": False}

            def finish(value):
                if guard["done"]:
                    return
                guard["done"] = True
                try:
                    dlg.destroy()
                except Exception:
                    pass
                try:
                    on_submit(value)
                except Exception:
                    traceback.print_exc()

            btns = tk.Frame(wrap, bg="#1e293b")
            btns.pack(side="bottom", fill="x", pady=(18, 0))
            tk.Button(btns, text="OK", width=10, relief="flat", cursor="hand2",
                      bg="#2563eb", fg="white", activebackground="#1d4ed8",
                      activeforeground="white", command=lambda: finish(var.get())
                      ).pack(side="right")
            tk.Button(btns, text="✕", width=4, relief="flat", cursor="hand2",
                      bg="#334155", fg="#e2e8f0", activebackground="#475569",
                      command=lambda: finish(None)).pack(side="right", padx=(0, 8))

            dlg.bind("<Return>", lambda e: finish(var.get()))
            dlg.bind("<Escape>", lambda e: finish(None))
            dlg.protocol("WM_DELETE_WINDOW", lambda: finish(None))

            sw, sh = dlg.winfo_screenwidth(), dlg.winfo_screenheight()
            x, y = (sw - W) // 2, (sh - H) // 3
            dlg.geometry(f"{W}x{H}+{x}+{y}")
            dlg.lift()
            dlg.focus_force()
            entry.focus_set()
            entry.icursor("end")
        except Exception:
            traceback.print_exc()
            try:
                on_submit(None)
            except Exception:
                pass

    def stop(self):
        self._q.put(None)
