"""Windows tizim ovozini pycaw (Core Audio API) orqali boshqarish."""

from ctypes import POINTER, cast

import comtypes
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume


class AudioController:
    """Master volume boshqaruvchisi.

    Diqqat: qaysi thread'da ishlatilsa, o'sha thread'da yaratilishi kerak
    (COM apartment talabi).
    """

    def __init__(self):
        comtypes.CoInitialize()
        self._endpoint = self._connect()

    def _connect(self):
        device = AudioUtilities.GetSpeakers()
        interface = device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        return cast(interface, POINTER(IAudioEndpointVolume))

    def set_volume(self, scalar: float) -> None:
        """scalar: 0.0 .. 1.0"""
        scalar = max(0.0, min(1.0, scalar))
        try:
            self._endpoint.SetMasterVolumeLevelScalar(scalar, None)
        except OSError:
            # Default audio qurilma o'zgargan bo'lishi mumkin - qayta ulanamiz
            self._endpoint = self._connect()
            self._endpoint.SetMasterVolumeLevelScalar(scalar, None)

    def get_volume(self) -> float:
        try:
            return self._endpoint.GetMasterVolumeLevelScalar()
        except OSError:
            self._endpoint = self._connect()
            return self._endpoint.GetMasterVolumeLevelScalar()

    def set_mute(self, mute: bool) -> None:
        try:
            self._endpoint.SetMute(mute, None)
        except OSError:
            self._endpoint = self._connect()
            self._endpoint.SetMute(mute, None)

    def is_muted(self) -> bool:
        try:
            return bool(self._endpoint.GetMute())
        except OSError:
            self._endpoint = self._connect()
            return bool(self._endpoint.GetMute())
