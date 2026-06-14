"""Aria orkestratori: enrollment → tinglash thread'i → system tray.

Oqim:
  1. Config/voiceprint/Recognizer yuklanadi.
  2. Voiceprint yo'q bo'lsa — enrollment oynasi (main thread).
  3. Tinglash worker thread'da; tray esa main thread'da (pystray.run bloklaydi).
  4. Tray'dan "Qayta yozish" yoki "Chiqish" — icon to'xtaydi, tashqi tsikl qaror qiladi.
"""

import sys
import threading

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
            self.recognizer = Recognizer(str(ASR_MODEL_DIR), str(SPK_MODEL_DIR))
        return self.recognizer

    # ---- Tinglash tsikli (worker thread) --------------------------------
    def _listen_loop(self):
        from .asr import Microphone
        from .audio_apps import AppAudio
        audio = AudioController()          # COM shu thread'da init bo'lishi shart
        app_audio = AppAudio()             # per-app sessiyalar (xuddi shu COM thread'i)
        tts = Speaker(self.cfg.voice_feedback)
        mic = Microphone()
        try:
            mic.start()
            while not self._stop_event.is_set():
                data = mic.read(timeout=0.3)
                if not data:
                    continue
                utt = self.recognizer.accept(data)
                if utt and utt.text:  # bo'sh matnlarni e'tiborsiz qoldiramiz
                    self._handle(utt, audio, app_audio, tts)
        finally:
            mic.stop()

    def _is_owner(self, utt) -> bool:
        """Speaker tasdiqlash. allow_all yoqilgan yoki voiceprint yo'q bo'lsa — True."""
        if self.cfg.allow_all_users or not self.voiceprint.exists():
            return True
        return self.voiceprint.verify(utt.spk, self.cfg.speaker_threshold)

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
        import time
        self._active_until = time.monotonic() + self.ACTIVE_WINDOW
        if self.cfg.voice_feedback:
            threading.Thread(target=self._beep, daemon=True).start()
        if self._overlay is not None:
            self._overlay.set_enabled(self.cfg.overlay_enabled)
            self._overlay.show("🎙 " + self.i18n.t("overlay_listening"))

    def _handle(self, utt, audio, app_audio, tts):
        import time
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

        def toggle_wake(icon, item):
            self.cfg.wake_word_enabled = not self.cfg.wake_word_enabled
            config_mod.save(self.cfg)
            icon.update_menu()

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
            MenuItem(tr("menu_wake_word"), toggle_wake,
                     checked=lambda i: self.cfg.wake_word_enabled),
            MenuItem(tr("menu_voice_feedback"), toggle_feedback,
                     checked=lambda i: self.cfg.voice_feedback),
            MenuItem(tr("menu_overlay"), toggle_overlay,
                     checked=lambda i: self.cfg.overlay_enabled),
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

        while True:
            self._reenroll = False
            self._quit = False

            # Enrollment kerakmi?
            if not self.voiceprint.exists() or self._pending_enroll():
                from .paths import VOICEPRINT_PATH
                print(f"Voiceprint yo'q ({VOICEPRINT_PATH}) — ovozni tanishtirish oynasi ochiladi.")
                from .enroll import run_enrollment
                ok = run_enrollment(self.recognizer, self.voiceprint, self.i18n)
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

        self._shutdown()
        return 0

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
