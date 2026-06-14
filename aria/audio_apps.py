"""Per-app (alohida ilova) ovozini boshqarish — pycaw audio sessiyalari orqali.

Har bir ilovaning ovozi alohida sessiya. Jarayon nomiga qarab topib, o'sha
sessiyaning volume/mute'ini o'zgartiramiz. "app" kaliti esa — hozir eng baland
o'ynayotgan ilovani (peak meter bo'yicha) tanlaydi.
"""

from .commands import APP_PROCESS_MAP

# Aktiv ilovani tanlashda e'tiborga olinmaydigan tizim jarayonlari
_EXCLUDE = {"audiodg.exe", "svchost.exe", "system", "explorer.exe",
            "shellexperiencehost.exe", "python.exe", "pythonw.exe", "aria.exe"}


class AppAudio:
    """pycaw sessiyalari ustida ishlovchi. Listener thread'ida (COM init) yaratiladi."""

    @staticmethod
    def _sessions():
        from pycaw.pycaw import AudioUtilities
        try:
            return AudioUtilities.GetAllSessions()
        except Exception:
            return []

    @staticmethod
    def _proc_name(session) -> str:
        try:
            return session.Process.name().lower() if session.Process else ""
        except Exception:
            return ""

    def _match(self, substrings):
        res = []
        for s in self._sessions():
            name = self._proc_name(s)
            if name and any(sub in name for sub in substrings):
                res.append(s)
        return res

    def _active(self):
        """Hozir eng baland o'ynayotgan ilova sessiyasi (peak meter bo'yicha)."""
        from pycaw.pycaw import IAudioMeterInformation
        best, best_peak = None, -1.0
        for s in self._sessions():
            name = self._proc_name(s)
            if not name or name in _EXCLUDE:
                continue
            try:
                peak = s._ctl.QueryInterface(IAudioMeterInformation).GetPeakValue()
            except Exception:
                peak = 0.0
            if peak > best_peak:
                best, best_peak = s, peak
        return [best] if best else []

    def targets(self, app_keyword: str):
        """app kalitiga mos sessiyalar ro'yxati."""
        if app_keyword == "app":
            return self._active()
        return self._match(APP_PROCESS_MAP.get(app_keyword, [app_keyword]))

    # ---- amallar ----
    @staticmethod
    def set_volume(sessions, scalar: float) -> None:
        scalar = max(0.0, min(1.0, scalar))
        for s in sessions:
            try:
                s.SimpleAudioVolume.SetMasterVolume(scalar, None)
            except Exception:
                pass

    @staticmethod
    def set_mute(sessions, mute: bool) -> None:
        for s in sessions:
            try:
                s.SimpleAudioVolume.SetMute(1 if mute else 0, None)
            except Exception:
                pass

    @staticmethod
    def get_volume(sessions) -> float:
        for s in sessions:
            try:
                return s.SimpleAudioVolume.GetMasterVolume()
            except Exception:
                pass
        return 0.0

    def label(self, app_keyword: str, sessions) -> str:
        """Foydalanuvchiga ko'rsatiladigan nom (feedback uchun)."""
        if app_keyword == "app" and sessions:
            name = self._proc_name(sessions[0])
            return name[:-4] if name.endswith(".exe") else name or "app"
        return app_keyword
