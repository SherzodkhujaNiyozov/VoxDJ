"""Aria orkestratori: enrollment → tinglash thread'i → system tray.

Oqim:
  1. Config/voiceprint/Recognizer yuklanadi.
  2. Voiceprint yo'q bo'lsa — enrollment oynasi (main thread).
  3. Tinglash worker thread'da; tray esa main thread'da (pystray.run bloklaydi).
  4. Tray'dan "Qayta yozish" yoki "Chiqish" — icon to'xtaydi, tashqi tsikl qaror qiladi.
"""

import sys
import threading
import time

from . import APP_NAME, commands
from . import config as config_mod
from .audio import AudioController
from .i18n import I18n, LANG_NAMES
from .paths import ASR_MODEL_DIR, SPK_MODEL_DIR
from .speaker import Voiceprint
from .tts import Speaker


def _models_ready() -> bool:
    return ASR_MODEL_DIR.exists() and SPK_MODEL_DIR.exists()


class Aria:
    # "Aria" deyilgandan keyin buyruqlar wake'siz qabul qilinadigan oyna (soniya)
    ACTIVE_WINDOW = 8.0

    def __init__(self):
        self.cfg = config_mod.load()
        self.i18n = I18n(self.cfg.language)
        self.voiceprint = Voiceprint()
        self.recognizer = None  # lazy: og'ir yuklanadi

        self._stop_event = threading.Event()
        self._mic_restart = threading.Event()  # mic qurilmasi o'zgarganda set qilinadi
        self._cycle_next = False               # "microphone" buyrug'i: keyingi mic'ga o't
        self._owner_until = 0.0                # egasi yaqinda tasdiqlangan vaqt (monotonic)
        # PortAudio init/terminate va query_devices THREAD-SAFE emas — listener
        # (refresh) va Tk oynasi (enumeratsiya) bir vaqtda chaqirmasligi uchun lock.
        self._pa_lock = threading.Lock()
        self._mic_win = None                   # ochiq mikrofon sozlamalari oynasi
        self._mic_repopulate = None            # oynani qayta chizish callback'i
        self._reenroll = False
        self._quit = False
        self._listener_thread = None
        self._icon = None
        self._overlay = None
        self._active_until = 0.0  # wake aktiv oynasining tugash vaqti (monotonic)

    # ---- Modellar -------------------------------------------------------
    def _ensure_recognizer(self):
        if self.recognizer is None:
            from vosk import SetLogLevel
            SetLogLevel(-1)  # Vosk shovqinli loglarini o'chiramiz
            from .asr import Recognizer
            self.recognizer = Recognizer(
                str(ASR_MODEL_DIR), str(SPK_MODEL_DIR),
                wake_word=self.cfg.wake_word,
                wake_alts=self.cfg.wake_alts,
            )
            # commands moduli wake set'ini sinxronlaymiz
            commands.WAKE_WORDS = {self.cfg.wake_word} | set(self.cfg.wake_alts)
        return self.recognizer

    # ---- Tinglash tsikli (worker thread) --------------------------------
    def _listen_loop(self):
        from .asr import Microphone
        from .audio_apps import AppAudio
        audio = AudioController()          # COM shu thread'da init bo'lishi shart
        app_audio = AppAudio()             # per-app sessiyalar (xuddi shu COM thread'i)
        tts = Speaker(self.cfg.voice_feedback)

        from . import asr as _asr
        # Tashqi tsikl: mic qurilmasi o'zgarganda qayta yaratiladi
        while not self._stop_event.is_set():
            self._mic_restart.clear()
            # PortAudio'ni yangilaymiz (stream yopiq — xavfsiz) — yangi ulangan
            # naushnik/mikrofon shu yerda ko'rinadi. Lock: Tk oynasi enumeratsiya
            # qilayotgan paytda terminate/init qilmaslik uchun.
            with self._pa_lock:
                _asr.refresh_devices()
            if self._cycle_next:                  # "microphone" buyrug'i kutyapti
                self._cycle_next = False
                self._advance_mic()               # yangilangan ro'yxatdan keyingisiga
            mic = self._open_mic(Microphone)
            if mic is None:                       # hech qanday mic ochilmadi
                self._stop_event.wait(2.0)
                continue
            try:
                while not self._stop_event.is_set() and not self._mic_restart.is_set():
                    data = mic.read(timeout=0.3)
                    if not data:
                        continue
                    utt = self.recognizer.accept(data)
                    if utt and utt.text:  # bo'sh matnlarni e'tiborsiz qoldiramiz
                        self._handle(utt, audio, app_audio, tts)
            finally:
                mic.stop()
            # Mic o'zgardi — Kaldi buferini tozalaymiz va yangi qurilma bilan davom etamiz
            if self._mic_restart.is_set() and not self._stop_event.is_set():
                self.recognizer.restart()

    def _resolve_mic(self):
        """cfg.mic_name → joriy qurilma indeksi.

        Indekslar qayta ishga tushganda siljiydi, shuning uchun har safar nomdan
        topamiz. None → tizim default (yoki nom topilmadi). Yashirilgan mic tanlangan
        bo'lsa ham default'ga qaytamiz.
        """
        name = self.cfg.mic_name
        if not name or name in set(self.cfg.hidden_mics):
            return None
        for idx, dev_name in self._enumerate_mics():
            if dev_name == name:
                return idx
        print(f"[mic] Saqlangan mikrofon topilmadi: {name!r} — tizim default ishlatiladi")
        return None

    def _open_mic(self, Microphone):
        """Tanlangan mikrofonni ochadi; ishlamasa tizim default'iga qaytadi.

        Qaytaradi: ochilgan Microphone yoki None (hech narsa ochilmasa).
        """
        idx = self._resolve_mic()
        mic = Microphone(idx)
        try:
            mic.start()
            return mic
        except Exception as exc:
            label = self.cfg.mic_name or "default"
            print(f"[mic] Ochilmadi ({label}): {exc}")
            if idx is None:
                return None                       # default ham ishlamadi
            # Tanlangan qurilma ishlamadi — tizim default'iga qaytamiz
            print("[mic] Tizim default mikrofoniga qaytildi.")
            mic = Microphone(None)
            try:
                mic.start()
                return mic
            except Exception as exc2:
                print(f"[mic] Default ham ochilmadi: {exc2}")
                return None

    def _is_owner(self, utt) -> bool:
        """Speaker tasdiqlash (egasimi?).

        allow_all yoki voiceprint yo'q → har doim True.

        Aks holda x-vector cosine bilan solishtiramiz. MUHIM nozik joy: qisqa
        gaplar (masalan yakka "aria") ko'pincha spk=None beradi — ularni so'zsiz
        rad etsak, egasini ham rad etadi (bu "private rejimda tanimayabdi"
        muammosi edi). Shuning uchun: spk bo'lsa va mos kelsa — egani yaqin
        kelajak uchun "ishonchli" deb belgilaymiz; spk bo'lmagan qisqa gaplarni
        esa shu ishonch oynasi ichida qabul qilamiz.
        """
        if self.cfg.allow_all_users or not self.voiceprint.exists():
            return True
        if utt.spk is not None:
            sim = self.voiceprint.similarity(utt.spk)
            if sim >= self.cfg.speaker_threshold:
                self._owner_until = time.monotonic() + self.ACTIVE_WINDOW
                return True
            return False
        # spk yo'q (juda qisqa gap) — egasi yaqinda tasdiqlangan bo'lsa ishonamiz
        return time.monotonic() < self._owner_until

    @staticmethod
    def _beep() -> None:
        try:
            import winsound
            winsound.Beep(880, 110)
        except Exception:
            pass

    def _activate(self, tts) -> None:
        """Wake so'zidan keyin aktiv oynani ochadi va qisqa signal beradi.

        DIQQAT: winsound.Beep ovoz o'chirilgan (muted) qurilmada bloklab qolishi
        mumkin — shuning uchun ALOHIDA thread'da chalamiz, aks holda tinglash
        thread'i osilib, mute'dan keyin buyruqlar o'qilmay qoladi.
        """
        self._active_until = time.monotonic() + self.ACTIVE_WINDOW
        if self.cfg.voice_feedback:
            threading.Thread(target=self._beep, daemon=True).start()
        if self._overlay is not None:
            self._overlay.set_enabled(self.cfg.overlay_enabled)
            self._overlay.show("🎙 " + self.i18n.t("overlay_listening"))

    def _handle(self, utt, audio, app_audio, tts):
        tokens = utt.text.split()
        had_wake, rest = commands.strip_wake(tokens)

        if self.cfg.wake_word_enabled:
            if had_wake:
                # Faqat egasi uyg'ota oladi (owner-only rejimda)
                if not self._is_owner(utt):
                    return
                self._activate(tts)
                if not rest:
                    return  # "Aria" yolg'iz aytildi — keyingi gapni buyruq sifatida kutamiz
                command_tokens = rest          # "Aria play" — bir nafasda
            elif time.monotonic() < self._active_until:
                command_tokens = tokens        # aktiv oyna ichida — wake shart emas
            else:
                return                          # wake ham yo'q, aktiv ham emas
        else:
            command_tokens = tokens            # wake o'chirilgan — har doim tinglaymiz

        cmd = commands.parse(" ".join(command_tokens))
        if cmd is None:
            return
        if not self._is_owner(utt):
            return  # egasi emas — jim rad etamiz

        feedback = self._execute(cmd, audio, app_audio)
        if feedback:
            self._active_until = time.monotonic() + self.ACTIVE_WINDOW  # oynani uzaytiramiz
            tts.set_enabled(self.cfg.voice_feedback)
            tts.say(feedback)
            if self._overlay is not None:
                self._overlay.set_enabled(self.cfg.overlay_enabled)
                self._overlay.show(feedback)

    def _execute(self, cmd, audio, app_audio) -> str:
        from . import media
        k = cmd.kind

        # --- Media boshqaruvi: har doim global (alohida ilovaga yo'naltirib bo'lmaydi) ---
        if k == commands.PLAY:
            media.play_pause(); return "Playing"
        if k == commands.PAUSE:
            media.play_pause(); return "Paused"
        if k == commands.STOP:
            media.stop(); return "Stopped"
        if k == commands.NEXT:
            media.next_track(); return "Next track"
        if k == commands.PREV:
            media.previous_track(); return "Previous track"

        if k == commands.ALLOW_ALL:
            self.cfg.allow_all_users = bool(cmd.value)
            config_mod.save(self.cfg)
            self._refresh_tray()
            return "Everyone can control" if cmd.value else "Owner only"

        if k == commands.CHANGE_MIC:
            return self._next_mic()

        # --- Ovoz/mute: ilova kaliti bo'lsa — o'sha ilovaga, aks holda master ---
        if cmd.app:
            return self._execute_app(cmd, app_audio)

        if k == commands.MUTE:
            audio.set_mute(True); return "Muted"
        if k == commands.UNMUTE:
            audio.set_mute(False); return "Unmuted"
        if k == commands.SET_VOLUME:
            audio.set_mute(False)
            audio.set_volume(cmd.value / 100.0)
            return f"Volume {cmd.value} percent"
        if k in (commands.VOL_UP, commands.VOL_DOWN):
            cur = round(audio.get_volume() * 100)
            step = self.cfg.volume_step * (1 if k == commands.VOL_UP else -1)
            new = max(0, min(100, cur + step))
            audio.set_volume(new / 100.0)
            return f"Volume {new} percent"
        return ""

    def _enumerate_mics(self):
        """Barcha WASAPI mic'lari (lock bilan — PortAudio thread-safe emas)."""
        from .asr import list_input_devices
        with self._pa_lock:
            return list_input_devices()

    def _visible_mics(self):
        """Yashirilmagan mikrofonlar (hidden_mics chiqarilgan)."""
        hidden = set(self.cfg.hidden_mics)
        return [(i, n) for i, n in self._enumerate_mics() if n not in hidden]

    def _next_mic(self) -> str:
        """Ovozli "microphone" buyrug'i — keyingi mic'ga o'tishni so'raydi.

        Haqiqiy o'tish listener thread'ida PortAudio yangilangach bajariladi
        (_advance_mic) — shunda yangi ulangan qurilma ham ro'yxatga kiradi.
        """
        self._cycle_next = True
        self._mic_restart.set()
        # Feedback uchun joriy (yangilanishidan oldingi) ro'yxatdan taxminiy nom
        names = [n for _, n in self._visible_mics()]
        if not names:
            return "Microphone…"
        cur = self.cfg.mic_name
        pos = names.index(cur) if cur in names else -1
        return f"Microphone {names[(pos + 1) % len(names)][:25]}"

    def _advance_mic(self) -> None:
        """Yashirilmagan mic'lar bo'ylab keyingisiga o'tadi (PortAudio yangilangach)."""
        names = [n for _, n in self._visible_mics()]
        if not names:
            return
        cur = self.cfg.mic_name
        pos = names.index(cur) if cur in names else -1
        self.cfg.mic_name = names[(pos + 1) % len(names)]
        config_mod.save(self.cfg)
        self._refresh_tray()

    # ---- Mikrofon sozlamalari oynasi (tanlash + yashirish, ochiq qoladi) -----
    def _open_mic_window(self, icon=None, item=None):
        """Tray'dan chaqiriladi — mikrofon sozlamalari oynasini ochadi.

        Oyna ochiq qoladi: bir necha mikrofonni ketma-ket tanlash/yashirish mumkin
        (tray menyu har bosishda yopilardi — shuning uchun alohida oyna). Ochilganda
        va "Refresh" bosilganda PortAudio yangilanadi — yangi ulangan qurilma chiqadi.
        """
        if self._overlay is None:
            return
        self._overlay.run_on_tk(self._build_mic_window)

    def _build_mic_window(self, root):
        import tkinter as tk
        import traceback
        # Allaqachon ochiq bo'lsa — old planga chiqaramiz
        if self._mic_win is not None:
            try:
                self._mic_win.deiconify(); self._mic_win.lift(); self._mic_win.focus_force()
                return
            except Exception:
                self._mic_win = None
        try:
            W, H = 500, 440
            win = tk.Toplevel(root)
            self._mic_win = win
            win.title(f"{self.i18n.t('menu_mic')} — {APP_NAME}")
            win.configure(bg="#0f172a")
            win.attributes("-topmost", True)

            tk.Label(win, text=self.i18n.t("menu_mic"), bg="#0f172a", fg="#f1f5f9",
                     font=("Segoe UI", 15, "bold")).pack(anchor="w", padx=22, pady=(18, 2))
            tk.Label(win, text=self.i18n.t("mic_hint"),
                     bg="#0f172a", fg="#94a3b8",
                     font=("Segoe UI", 9)).pack(anchor="w", padx=22)

            list_frame = tk.Frame(win, bg="#0f172a")
            list_frame.pack(fill="both", expand=True, padx=16, pady=12)

            def repopulate():
                if self._mic_win is None:
                    return
                for w in list_frame.winfo_children():
                    w.destroy()
                self._mic_row(list_frame, None, self.i18n.t("menu_mic_default"),
                              is_default=True)
                hidden = set(self.cfg.hidden_mics)
                for _idx, name in self._enumerate_mics():
                    self._mic_row(list_frame, name, name, hidden=(name in hidden))

            self._mic_repopulate = repopulate
            repopulate()
            # Ochilgandan so'ng PortAudio yangilanib, yangi ulangan qurilma chiqishi uchun
            self._mic_restart.set()
            root.after(900, repopulate)

            btns = tk.Frame(win, bg="#0f172a")
            btns.pack(fill="x", padx=22, pady=(0, 16))

            def do_refresh():
                self._mic_restart.set()          # listener PortAudio'ni yangilaydi
                root.after(900, repopulate)

            tk.Button(btns, text=self.i18n.t("mic_refresh"), relief="flat", cursor="hand2",
                      bg="#334155", fg="#e2e8f0", activebackground="#475569",
                      activeforeground="white", command=do_refresh).pack(side="left")
            tk.Button(btns, text=self.i18n.t("btn_close"), relief="flat", cursor="hand2",
                      width=10, bg="#2563eb", fg="white", activebackground="#1d4ed8",
                      activeforeground="white", command=lambda: _close()).pack(side="right")

            def _close():
                self._mic_win = None
                self._mic_repopulate = None
                try:
                    win.destroy()
                except Exception:
                    pass

            win.protocol("WM_DELETE_WINDOW", _close)
            sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
            win.geometry(f"{W}x{H}+{(sw - W) // 2}+{(sh - H) // 3}")
            win.lift(); win.focus_force()
        except Exception:
            traceback.print_exc()
            self._mic_win = None

    def _mic_row(self, parent, name, label, is_default=False, hidden=False):
        """Oynadagi bitta qurilma qatori: [●/○ tanlash]  nom  [☑/☐ ko'rinish]."""
        import tkinter as tk
        active = (self.cfg.mic_name is None) if is_default else (self.cfg.mic_name == name)
        row = tk.Frame(parent, bg="#1e293b")
        row.pack(fill="x", pady=3, ipady=2)

        def select():
            if name is not None and name in self.cfg.hidden_mics:
                self.cfg.hidden_mics = [m for m in self.cfg.hidden_mics if m != name]
            self.cfg.mic_name = name
            config_mod.save(self.cfg)
            self._mic_restart.set()
            self._refresh_tray()
            if self._mic_repopulate:
                self._mic_repopulate()

        tk.Button(row, text=("●" if active else "○"), relief="flat", bd=0,
                  bg="#1e293b", fg=("#22c55e" if active else "#64748b"),
                  activebackground="#1e293b", font=("Segoe UI", 14),
                  cursor="hand2", command=select).pack(side="left", padx=(10, 6))
        tk.Label(row, text=label[:46], bg="#1e293b",
                 fg=("#64748b" if hidden else "#f1f5f9"),
                 font=("Segoe UI", 10)).pack(side="left", padx=4)

        if not is_default:
            def toggle_hide():
                h = list(self.cfg.hidden_mics)
                if name in h:
                    h.remove(name)
                else:
                    h.append(name)
                    if self.cfg.mic_name == name:    # aktiv yashirilsa — default'ga
                        self.cfg.mic_name = None
                        self._mic_restart.set()
                self.cfg.hidden_mics = h
                config_mod.save(self.cfg)
                self._refresh_tray()
                if self._mic_repopulate:
                    self._mic_repopulate()

            tk.Button(row, text=("☐" if hidden else "☑"), relief="flat", bd=0,
                      bg="#1e293b", fg=("#64748b" if hidden else "#38bdf8"),
                      activebackground="#1e293b", font=("Segoe UI", 13),
                      cursor="hand2", command=toggle_hide).pack(side="right", padx=10)

    def _execute_app(self, cmd, app_audio) -> str:
        """Alohida ilova ovozini boshqarish (spotify/chrome/.../app)."""
        sessions = app_audio.targets(cmd.app)
        label = app_audio.label(cmd.app, sessions).capitalize()
        if not sessions:
            return f"{label}: no audio"
        k = cmd.kind
        if k == commands.MUTE:
            app_audio.set_mute(sessions, True); return f"{label} muted"
        if k == commands.UNMUTE:
            app_audio.set_mute(sessions, False); return f"{label} unmuted"
        if k == commands.SET_VOLUME:
            app_audio.set_mute(sessions, False)
            app_audio.set_volume(sessions, cmd.value / 100.0)
            return f"{label} {cmd.value} percent"
        if k in (commands.VOL_UP, commands.VOL_DOWN):
            cur = round(app_audio.get_volume(sessions) * 100)
            step = self.cfg.volume_step * (1 if k == commands.VOL_UP else -1)
            new = max(0, min(100, cur + step))
            app_audio.set_volume(sessions, new / 100.0)
            return f"{label} {new} percent"
        return ""

    # ---- Tray -----------------------------------------------------------
    def _build_icon(self):
        import pystray
        from pystray import Menu, MenuItem
        from .tray_icon import make_icon

        # Menyu yorliqlari callable — til o'zgarsa, update_menu() yetarli
        def tr(key):
            return lambda item: self.i18n.t(key)

        def status_text(item):
            return self.i18n.t("menu_status_all") if self.cfg.allow_all_users \
                else self.i18n.t("menu_status_owner")

        def toggle_allow_all(icon, item):
            self.cfg.allow_all_users = not self.cfg.allow_all_users
            config_mod.save(self.cfg)
            icon.update_menu()

        def toggle_wake_enabled(icon, item):
            self.cfg.wake_word_enabled = not self.cfg.wake_word_enabled
            config_mod.save(self.cfg)
            icon.update_menu()

        # Wake word presetlari: (ko'rsatiladigan nom, so'z, fonetik variantlar)
        _WAKE_PRESETS = [
            (self.i18n.t("menu_wake_aria"),   "aria",   ["area"]),
            (self.i18n.t("menu_wake_vox"),    "vox",    []),
            (self.i18n.t("menu_wake_jarvis"), "jarvis", []),
        ]

        def make_wake_setter(word, alts):
            def setter(icon, item):
                self.cfg.wake_word = word
                self.cfg.wake_alts = alts[:]
                config_mod.save(self.cfg)
                commands.WAKE_WORDS = {word} | set(alts)
                if self.recognizer:
                    self.recognizer.set_wake(word, alts)
                icon.update_menu()
            return setter

        def set_custom_wake(icon, item):
            # Dialog overlay'ning Tk thread'ida ASINXRON ochiladi — tray muzlamaydi.
            # Tasdiqlanganda apply() o'sha Tk thread'ida chaqiriladi.
            if self._overlay is None:
                return

            def apply(word):
                if not word:
                    return
                # Faqat harf va bo'shliq (grammatika xavfsizligi), 1–20 belgi
                word2 = "".join(c for c in word.lower()
                                if c.isalpha() or c == " ").strip()[:20]
                if not word2:
                    return
                self.cfg.wake_word = word2
                self.cfg.wake_alts = []
                config_mod.save(self.cfg)
                commands.WAKE_WORDS = {word2}
                if self.recognizer:
                    self.recognizer.set_wake(word2, [])
                self._refresh_tray()

            self._overlay.ask_text(
                self.i18n.t("menu_wake_word"),
                self.i18n.t("menu_wake_custom_prompt"),
                self.cfg.wake_word,
                apply,
            )

        wake_submenu = Menu(
            *[
                MenuItem(name, make_wake_setter(word, alts),
                         checked=lambda i, w=word: self.cfg.wake_word == w,
                         radio=True)
                for name, word, alts in _WAKE_PRESETS
            ],
            Menu.SEPARATOR,
            MenuItem(tr("menu_wake_custom"), set_custom_wake),
        )

        # Mikrofon: tanlash + yashirish endi ALOHIDA OYNADA (tray menyu har bosishda
        # yopilardi — bir nechta mic'ni ketma-ket sozlab bo'lmasdi). Oyna ochiq qoladi
        # va ochilganda PortAudio yangilanadi (yangi ulangan qurilma ko'rinadi).

        def toggle_feedback(icon, item):
            self.cfg.voice_feedback = not self.cfg.voice_feedback
            config_mod.save(self.cfg)
            icon.update_menu()

        def toggle_overlay(icon, item):
            self.cfg.overlay_enabled = not self.cfg.overlay_enabled
            config_mod.save(self.cfg)
            if self._overlay is not None:
                self._overlay.set_enabled(self.cfg.overlay_enabled)
            icon.update_menu()

        def toggle_autostart(icon, item):
            from . import autostart
            new = not self.cfg.autostart
            try:
                autostart.set_enabled(new)
                self.cfg.autostart = new
                config_mod.save(self.cfg)
            except OSError:
                pass
            icon.update_menu()

        def make_lang_setter(code):
            def setter(icon, item):
                self.cfg.language = code
                self.i18n.set_lang(code)
                config_mod.save(self.cfg)
                icon.title = self.i18n.t("tray_title")
                icon.update_menu()  # yorliqlar callable — yangi tilda qayta chiziladi
            return setter

        def do_reenroll(icon, item):
            self._reenroll = True
            icon.stop()

        def do_quit(icon, item):
            self._quit = True
            icon.stop()

        menu = Menu(
            MenuItem(status_text, None, enabled=False),
            Menu.SEPARATOR,
            MenuItem(tr("menu_allow_all"), toggle_allow_all,
                     checked=lambda i: self.cfg.allow_all_users),
            MenuItem(tr("menu_wake_word"), wake_submenu),
            MenuItem(tr("menu_wake_enabled"), toggle_wake_enabled,
                     checked=lambda i: self.cfg.wake_word_enabled),
            MenuItem(tr("menu_voice_feedback"), toggle_feedback,
                     checked=lambda i: self.cfg.voice_feedback),
            MenuItem(tr("menu_overlay"), toggle_overlay,
                     checked=lambda i: self.cfg.overlay_enabled),
            Menu.SEPARATOR,
            MenuItem(tr("menu_mic"), self._open_mic_window),
            Menu.SEPARATOR,
            MenuItem(tr("menu_language"), Menu(*[
                MenuItem(LANG_NAMES[code], make_lang_setter(code),
                         checked=lambda i, c=code: self.cfg.language == c,
                         radio=True)
                for code in LANG_NAMES
            ])),
            MenuItem(tr("menu_reenroll"), do_reenroll),
            MenuItem(tr("menu_autostart"), toggle_autostart,
                     checked=lambda i: self.cfg.autostart),
            Menu.SEPARATOR,
            MenuItem(tr("menu_quit"), do_quit),
        )
        self._icon = pystray.Icon(
            APP_NAME, make_icon(True), self.i18n.t("tray_title"), menu=menu,
        )
        return self._icon

    def _refresh_tray(self):
        if self._icon is not None:
            try:
                self._icon.update_menu()
            except Exception:
                pass

    # ---- Hayot tsikli ---------------------------------------------------
    def run(self):
        if not _models_ready():
            print("Modellar topilmadi. Avval yuklab oling:\n  py download_models.py")
            return 1

        print("Aria ishga tushmoqda… (modellar yuklanmoqda)")
        self._ensure_recognizer()

        try:
            self._run_loop()
        except KeyboardInterrupt:
            pass
        finally:
            # Har qanday holatda (toza chiqish, Ctrl+C, kutilmagan xato) toza yopamiz:
            # listener to'xtaydi, overlay Tk thread'i quit qiladi (destroy YO'Q —
            # Tcl_AsyncDelete panic'ining oldini olish uchun).
            self._stop_event.set()
            if self._listener_thread is not None:
                self._listener_thread.join(timeout=2.0)
            if self._overlay is not None:
                self._overlay.stop()
                self._overlay = None
        self._shutdown()
        return 0

    def _run_loop(self):
        while True:
            self._reenroll = False
            self._quit = False

            # Enrollment kerakmi?
            if not self.voiceprint.exists() or self._pending_enroll():
                from .paths import VOICEPRINT_PATH
                if self.voiceprint.exists():
                    print("Ovozni qayta yozish so'raldi — tanishtirish oynasi ochiladi.")
                else:
                    print(f"Voiceprint yo'q ({VOICEPRINT_PATH}) — tanishtirish oynasi ochiladi.")
                from . import asr as _asr
                _asr.refresh_devices()                  # yangi qurilmalarni ko'rish
                dev = self._resolve_mic()               # tinglashdagi AYNI mikrofon
                from .enroll import run_enrollment
                ok = run_enrollment(self.recognizer, self.voiceprint, self.i18n,
                                    self.cfg.wake_word, device=dev)
                if ok:
                    # Yangi ovoz izi — chegarani standart (0.40) ga qaytaramiz,
                    # eski yuqori qiymat (0.45) egasini ko'p rad etardi.
                    self.cfg.speaker_threshold = config_mod.Config.speaker_threshold
                    config_mod.save(self.cfg)
                print("Enrollment:", "saqlandi ✓" if ok else "saqlanmadi ✗ (ovoz olinmadi)")
            else:
                print("Voiceprint topildi — enrollment o'tkazib yuborildi (faqat egasi).")

            # Overlay (enrollment'dan keyin — Tk to'qnashuvi bo'lmasligi uchun)
            from .overlay import Overlay
            self._overlay = Overlay(self.cfg.overlay_enabled)

            # Tinglashni boshlaymiz
            self._stop_event.clear()
            self._listener_thread = threading.Thread(
                target=self._listen_loop, daemon=True)
            self._listener_thread.start()

            # Tray (bloklaydi, icon.stop() gacha)
            icon = self._build_icon()
            icon.run()

            # Tray to'xtadi — tinglashni va overlay'ni to'xtatamiz
            self._stop_event.set()
            self._listener_thread.join(timeout=2.0)
            if self._overlay is not None:
                self._overlay.stop()
                self._overlay = None

            if self._reenroll:
                self.voiceprint = Voiceprint()  # eski izni qayta yuklash
                self._force_enroll = True
                continue
            break

    _force_enroll = False

    def _pending_enroll(self) -> bool:
        if self._force_enroll:
            self._force_enroll = False
            return True
        return False

    def _shutdown(self):
        # Kafolatlangan chiqish (watchdog) — har ehtimolga qarshi
        def _kill():
            import os, time
            time.sleep(3.0)
            os._exit(0)
        threading.Thread(target=_kill, daemon=True).start()


def main() -> int:
    try:
        return Aria().run()
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
