"""Windows tizim ovozini pycaw (Core Audio API) orqali boshqarish."""

from ctypes import POINTER, cast

import comtypes
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume


class AudioController:
    """Master volume boshqaruvchisi.

    Diqqat: qaysi thread'da ishlatilsa, o'sha thread'da yaratilishi kerak
    (COM apartment talabi).

    MUHIM: har amalda JORIY default chiqish qurilmasini qaytadan aniqlaymiz.
    Aks holda (eski kod kabi endpoint'ni keshlash) — naushnik uzilib, default
    qurilma o'zgarsa, buyruq hali ham eski (uzilgan) qurilmaga borardi va PC
    ovozi o'zgarmasdi. GetSpeakers() doim joriy default'ni qaytaradi.
    """

    def __init__(self):
        comtypes.CoInitialize()

    def _endpoint(self):
        """Joriy default chiqish qurilmasining volume interfeysi (har safar yangi)."""
        device = AudioUtilities.GetSpeakers()
        interface = device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        return cast(interface, POINTER(IAudioEndpointVolume))

    def set_volume(self, scalar: float) -> None:
        """scalar: 0.0 .. 1.0"""
        scalar = max(0.0, min(1.0, scalar))
        self._endpoint().SetMasterVolumeLevelScalar(scalar, None)

    def get_volume(self) -> float:
        return self._endpoint().GetMasterVolumeLevelScalar()

    def set_mute(self, mute: bool) -> None:
        self._endpoint().SetMute(mute, None)

    def is_muted(self) -> bool:
        return bool(self._endpoint().GetMute())
