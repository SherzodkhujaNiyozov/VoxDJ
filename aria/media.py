"""Media boshqaruv tugmalari (play/pause, next, previous, stop).

Windows virtual-key media kalitlarini ctypes orqali yuboramiz — bu istalgan
media pleyer (Spotify, brauzer, AIMP, ...) tushunadigan tizim darajasidagi signal.
Qo'shimcha kutubxona kerak emas.
"""

import ctypes

_KEYEVENTF_EXTENDEDKEY = 0x0001
_KEYEVENTF_KEYUP = 0x0002

# Virtual-key kodlari (Windows)
_VK_MEDIA_NEXT_TRACK = 0xB0
_VK_MEDIA_PREV_TRACK = 0xB1
_VK_MEDIA_STOP = 0xB2
_VK_MEDIA_PLAY_PAUSE = 0xB3


def _tap(vk: int) -> None:
    user32 = ctypes.windll.user32
    user32.keybd_event(vk, 0, _KEYEVENTF_EXTENDEDKEY, 0)
    user32.keybd_event(vk, 0, _KEYEVENTF_EXTENDEDKEY | _KEYEVENTF_KEYUP, 0)


def play_pause() -> None:
    """Play/Pause — bu tizim darajasida bitta toggle tugma."""
    _tap(_VK_MEDIA_PLAY_PAUSE)


def next_track() -> None:
    _tap(_VK_MEDIA_NEXT_TRACK)


def previous_track() -> None:
    _tap(_VK_MEDIA_PREV_TRACK)


def stop() -> None:
    _tap(_VK_MEDIA_STOP)
