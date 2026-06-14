"""Tanilgan inglizcha matnni buyruqqa aylantirish (parsing).

Buyruqlar har doim inglizcha. Bajarish app.py da (audio/media controllerlar bilan).
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple

# Uyg'otish so'zlari — app.py tomonidan yangilanadi (foydalanuvchi wake word o'zgartirganda).
# Default: "aria" + "area" fonetik variant. Mutable set — to'g'ridan-to'g'ri almashtiring:
#   commands.WAKE_WORDS = {cfg.wake_word} | set(cfg.wake_alts)
WAKE_WORDS: set = {"aria", "area"}

# Yakka raqamlar (raqamma-raqam usuli uchun — eng ishonchli): "five zero" = 50
_DIGIT = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
          "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9}
# Qo'shma so'zlar (model tanisa ishlatamiz): "fifty" = 50, "seventeen" = 17
_UNITS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19,
}
_TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
         "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}
_NUMWORDS = set(_DIGIT) | set(_UNITS) | set(_TENS) | {"hundred"}

# Buyruq turlari
PLAY, PAUSE, STOP = "PLAY", "PAUSE", "STOP"
NEXT, PREV = "NEXT", "PREV"
MUTE, UNMUTE = "MUTE", "UNMUTE"
SET_VOLUME, VOL_UP, VOL_DOWN = "SET_VOLUME", "VOL_UP", "VOL_DOWN"
ALLOW_ALL = "ALLOW_ALL"    # value: 1 (hamma) yoki 0 (faqat egasi)
CHANGE_MIC = "CHANGE_MIC"  # keyingi mikrofon qurilmasiga o'tish

# Per-app: tanilgan ilova kaliti -> jarayon nomi(lari) ichidagi bo'lak.
# Faqat kichik model ANIQ tanийdigan nomlar (test bilan tanlangan).
# "app" — maxsus: hozir eng baland o'ynayotgan ilova.
APP_PROCESS_MAP = {
    "spotify": ["spotify"],
    "chrome": ["chrome"],
    "firefox": ["firefox"],
    "edge": ["msedge"],
    "youtube": ["chrome", "msedge", "firefox", "opera", "brave", "vivaldi"],
    "telegram": ["telegram"],
    "music": ["spotify", "music", "aimp", "foobar", "wmplayer", "itunes", "музыка"],
    "app": [],  # maxsus — aktiv sessiya
}
APP_KEYWORDS = set(APP_PROCESS_MAP)


@dataclass
class Command:
    kind: str
    value: Optional[int] = None
    app: Optional[str] = None  # per-app bo'lsa — ilova kaliti (masalan "spotify")


def words_to_number(tokens: List[str]) -> Optional[int]:
    """Ovozli raqamni 0..100 ga aylantiradi.

    Eng ishonchli usul — raqamma-raqam (model "twenty"ni ko'pincha tanimaydi,
    lekin "two zero"ni aniq tanidi):
      "five zero"     -> 50
      "two zero"      -> 20
      "one zero zero" -> 100
      "seven five"    -> 75
    Qo'shma so'zlar ham qo'llab-quvvatlanadi (model tanisa):
      "fifty" -> 50,  "seventeen" -> 17,  "one hundred" -> 100
    """
    nums = [t for t in tokens if t in _NUMWORDS]
    if not nums:
        return None

    # Hammasi yakka raqam bo'lsa — raqamlarni ketma-ket biriktiramiz
    if all(t in _DIGIT for t in nums):
        if len(nums) == 1:
            return _DIGIT[nums[0]]
        val = int("".join(str(_DIGIT[t]) for t in nums))
        return min(val, 100)

    # Aks holda — qo'shma so'zlar (o'nlik + birlik + yuz)
    total = 0
    for t in nums:
        if t in _TENS:
            total += _TENS[t]
        elif t in _UNITS:
            total += _UNITS[t]
        elif t == "hundred":
            total = (total or 1) * 100
    return min(total, 100)


def strip_wake(tokens: List[str]) -> Tuple[bool, List[str]]:
    """Uyg'otish so'zini topadi va olib tashlaydi.

    Returns: (uyg'otish so'zi bor edimi, qolgan tokenlar).
    """
    had_wake = False
    out = []
    for tok in tokens:
        if tok in WAKE_WORDS and not out:  # faqat boshidagi wake hisobga olinadi
            had_wake = True
            continue
        out.append(tok)
    return had_wake, out


# Buyruq so'zlarining ishonchli sinonimlari (model ba'zan shularga adashadi yoki
# foydalanuvchi shularni aytadi). Grammatikaga ham qo'shilgan.
# "next" kichik modelda [unk] bo'ladi; "skip" aniq tanildi → asosiy so'z "skip".
# "forward" "four"ni o'g'irlagani uchun olib tashlandi.
_NEXT_WORDS = {"skip", "next"}
_PREV_WORDS = {"previous", "back", "previously"}
_AUDIO_WORDS = {"audio", "volume", "sound"}
# "unmute" modelda YO'Q (OOV) — doim "only mute" bo'lib chiqadi; shuni ushlaymiz.
# ("on" grammatikadan olib tashlandi — u "one"ni o'g'irlardi)
_UNMUTE_HINTS = {"unmute", "only", "un"}


def parse(text: str) -> Optional[Command]:
    """Buyruq matnini Command'ga aylantiradi (wake so'zsiz, aktiv holatda kutiladi).

    Agar ilova kaliti bo'lsa ("aria spotify five zero"), buyruq o'sha ilovaga
    yo'naltiriladi (cmd.app).
    """
    tokens = [t for t in text.lower().split() if t and t != "[unk]"]
    if not tokens:
        return None
    s = set(tokens)
    app = next((k for k in APP_KEYWORDS if k in s), None)
    cmd = _parse_action(tokens, s, app is not None)
    if cmd is not None and cmd.kind not in (ALLOW_ALL, CHANGE_MIC):
        cmd.app = app  # rejim almashtirish va mic o'zgartirish ilovaga bog'lanmaydi
    return cmd


def _parse_action(tokens, s, app_present: bool) -> Optional[Command]:
    has_audio = bool(_AUDIO_WORDS & s)
    number = words_to_number(tokens)

    # --- Aniq foiz (BIRINCHI): raqam + (volume/app/percent) bo'lsa, bu ovoz buyrug'i.
    # Model ba'zan "volume five zero"ga tasodifan "mute" qo'shadi — raqam bo'lsa,
    # uni e'tiborsiz qoldirib SET_VOLUME qilamiz (mute'dan ustun). ---
    if number is not None and (has_audio or "percent" in s or app_present):
        return Command(SET_VOLUME, max(0, min(100, number)))

    # --- Mute / Unmute (raqamsiz) ---
    if "unmute" in s:
        return Command(UNMUTE)
    if "mute" in s:
        # "un mute" / "on mute" -> unmute; sof "mute" -> mute
        return Command(UNMUTE) if (_UNMUTE_HINTS - {"unmute"}) & s else Command(MUTE)

    # --- Rejim almashtirish: "everyone" → hamma, "private" → faqat egasi ---
    # "everyone" — 3 bo'g'inli, raqam so'zlari bilan to'qnashmaydi.
    # "private" — xavfsiz fonetik (raqam so'zlari bilan o'xshashligi yo'q).
    if "everyone" in s:
        return Command(ALLOW_ALL, 1)
    if "private" in s:
        return Command(ALLOW_ALL, 0)

    # --- Mikrofon o'zgartirish ---
    if "microphone" in s:
        return Command(CHANGE_MIC)

    # --- Media boshqaruvi (global — alohida ilovaga yo'naltirib bo'lmaydi) ---
    if "play" in s:
        return Command(PLAY)
    if "pause" in s:
        return Command(PAUSE)
    if "stop" in s:
        return Command(STOP)
    if _NEXT_WORDS & s:
        return Command(NEXT)
    if _PREV_WORDS & s:
        return Command(PREV)

    # --- Nisbiy ovoz: louder/quieter (volume so'zi shart emas) ---
    if "louder" in s or (has_audio and "up" in s):
        return Command(VOL_UP)
    if "quieter" in s or (has_audio and "down" in s):
        return Command(VOL_DOWN)

    return None
