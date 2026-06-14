"""5 tilli interfeys (uz/en/es/ja/ru).

DIQQAT: bu faqat INTERFEYS uchun. Ovozli BUYRUQLAR har doim inglizcha
("play", "pause", "mute", "volume fifty percent", ...).
"""

STRINGS = {
    "uz": {
        "tray_title": "Aria — ovoz bilan audio",
        "menu_status_owner": "🔒 Faqat egasi boshqaradi",
        "menu_status_all": "🌐 Hamma boshqara oladi",
        "menu_allow_all": "Hamma boshqara olsin",
        "menu_wake_word": "Uyg'otish so'zi",
        "menu_wake_enabled": "Uyg'otish so'zini talab qilish",
        "menu_wake_aria": "Aria",
        "menu_wake_vox": "Vox",
        "menu_wake_jarvis": "Jarvis",
        "menu_wake_custom": "Maxsus…",
        "menu_wake_custom_prompt": "Uyg'otish so'zini kiriting:",
        "menu_mic": "Mikrofon",
        "menu_mic_default": "Tizim mikrofoni (default)",
        "menu_mic_manage": "Mikrofonlarni boshqarish",
        "menu_voice_feedback": "Ovozli javob",
        "menu_reenroll": "Ovozni qayta yozish",
        "menu_autostart": "Windows bilan ishga tushsin",
        "menu_language": "Til",
        "menu_quit": "Chiqish",
        "enroll_title": "Aria — ovozni tanishtirish",
        "enroll_intro": "Boshqaruv faqat sizning ovozingiz bilan bo'lishi uchun, "
                        "ovozingizni bir marta yozib olamiz.\n"
                        "Quyidagi jumlani tabiiy ohangda baland o'qing.",
        "enroll_phrase": "«{wake}, play the music. {wake}, volume five zero.»",
        "enroll_start": "Yozishni boshlash",
        "enroll_listening": "Tinglayapman… gapiring",
        "enroll_progress": "Namuna {n}/{total} olindi",
        "enroll_success": "Tayyor! Endi faqat sizning ovozingiz boshqaradi.",
        "enroll_failed": "Ovoz aniq chiqmadi. Yana urinib ko'ramizmi?",
        "enroll_retry": "Qayta urinish",
        "enroll_close": "Yopish",
        "notify_locked": "Bu sizning ovozingiz emas — buyruq rad etildi.",
    },
    "en": {
        "tray_title": "Aria — voice audio control",
        "menu_status_owner": "🔒 Owner only",
        "menu_status_all": "🌐 Anyone can control",
        "menu_allow_all": "Allow anyone to control",
        "menu_wake_word": "Wake word",
        "menu_wake_enabled": "Require wake word",
        "menu_wake_aria": "Aria",
        "menu_wake_vox": "Vox",
        "menu_wake_jarvis": "Jarvis",
        "menu_wake_custom": "Custom…",
        "menu_wake_custom_prompt": "Enter the wake word:",
        "menu_mic": "Microphone",
        "menu_mic_default": "System default",
        "menu_mic_manage": "Manage microphones",
        "menu_voice_feedback": "Voice feedback",
        "menu_reenroll": "Re-enroll my voice",
        "menu_autostart": "Start with Windows",
        "menu_language": "Language",
        "menu_quit": "Quit",
        "enroll_title": "Aria — voice enrollment",
        "enroll_intro": "So that only your voice controls the audio, we'll record "
                        "your voice once.\nRead the sentence below out loud, naturally.",
        "enroll_phrase": "\"{wake}, play the music. {wake}, volume five zero.\"",
        "enroll_start": "Start recording",
        "enroll_listening": "Listening… please speak",
        "enroll_progress": "Captured sample {n}/{total}",
        "enroll_success": "Done! Only your voice controls the audio now.",
        "enroll_failed": "Couldn't capture your voice clearly. Try again?",
        "enroll_retry": "Try again",
        "enroll_close": "Close",
        "notify_locked": "That's not your voice — command rejected.",
    },
    "es": {
        "tray_title": "Aria — control de audio por voz",
        "menu_status_owner": "🔒 Solo el dueño",
        "menu_status_all": "🌐 Cualquiera puede controlar",
        "menu_allow_all": "Permitir que cualquiera controle",
        "menu_wake_word": "Palabra de activación",
        "menu_wake_enabled": "Requerir palabra de activación",
        "menu_wake_aria": "Aria",
        "menu_wake_vox": "Vox",
        "menu_wake_jarvis": "Jarvis",
        "menu_wake_custom": "Personalizada…",
        "menu_wake_custom_prompt": "Introduce la palabra de activación:",
        "menu_mic": "Micrófono",
        "menu_mic_default": "Predeterminado del sistema",
        "menu_mic_manage": "Gestionar micrófonos",
        "menu_voice_feedback": "Respuesta por voz",
        "menu_reenroll": "Volver a registrar mi voz",
        "menu_autostart": "Iniciar con Windows",
        "menu_language": "Idioma",
        "menu_quit": "Salir",
        "enroll_title": "Aria — registro de voz",
        "enroll_intro": "Para que solo tu voz controle el audio, grabaremos tu voz "
                        "una vez.\nLee la siguiente frase en voz alta, con naturalidad.",
        "enroll_phrase": "\"{wake}, play the music. {wake}, volume five zero.\"",
        "enroll_start": "Empezar a grabar",
        "enroll_listening": "Escuchando… habla",
        "enroll_progress": "Muestra {n}/{total} capturada",
        "enroll_success": "¡Listo! Ahora solo tu voz controla el audio.",
        "enroll_failed": "No se captó bien tu voz. ¿Intentar de nuevo?",
        "enroll_retry": "Intentar de nuevo",
        "enroll_close": "Cerrar",
        "notify_locked": "Esa no es tu voz — comando rechazado.",
    },
    "ja": {
        "tray_title": "Aria — 音声オーディオ操作",
        "menu_status_owner": "🔒 所有者のみ",
        "menu_status_all": "🌐 誰でも操作可能",
        "menu_allow_all": "誰でも操作できるようにする",
        "menu_wake_word": "ウェイクワード",
        "menu_wake_enabled": "ウェイクワードを要求する",
        "menu_wake_aria": "Aria",
        "menu_wake_vox": "Vox",
        "menu_wake_jarvis": "Jarvis",
        "menu_wake_custom": "カスタム…",
        "menu_wake_custom_prompt": "ウェイクワードを入力してください:",
        "menu_mic": "マイク",
        "menu_mic_default": "システムデフォルト",
        "menu_mic_manage": "マイクの管理",
        "menu_voice_feedback": "音声フィードバック",
        "menu_reenroll": "自分の声を登録し直す",
        "menu_autostart": "Windows起動時に開始",
        "menu_language": "言語",
        "menu_quit": "終了",
        "enroll_title": "Aria — 声の登録",
        "enroll_intro": "あなたの声だけで操作できるように、声を一度録音します。\n"
                        "下の文を自然な声で読み上げてください。",
        "enroll_phrase": "「{wake}, play the music. {wake}, volume five zero.」",
        "enroll_start": "録音を開始",
        "enroll_listening": "聞いています…話してください",
        "enroll_progress": "サンプル {n}/{total} を取得",
        "enroll_success": "完了！これであなたの声だけが操作できます。",
        "enroll_failed": "声をうまく取得できませんでした。もう一度試しますか？",
        "enroll_retry": "もう一度",
        "enroll_close": "閉じる",
        "notify_locked": "あなたの声ではありません — コマンドを拒否しました。",
    },
    "ru": {
        "tray_title": "Aria — управление звуком голосом",
        "menu_status_owner": "🔒 Только владелец",
        "menu_status_all": "🌐 Управлять может любой",
        "menu_allow_all": "Разрешить управление всем",
        "menu_wake_word": "Слово активации",
        "menu_wake_enabled": "Требовать слово активации",
        "menu_wake_aria": "Aria",
        "menu_wake_vox": "Vox",
        "menu_wake_jarvis": "Jarvis",
        "menu_wake_custom": "Своё…",
        "menu_wake_custom_prompt": "Введите слово активации:",
        "menu_mic": "Микрофон",
        "menu_mic_default": "Системный по умолчанию",
        "menu_mic_manage": "Управление микрофонами",
        "menu_voice_feedback": "Голосовой ответ",
        "menu_reenroll": "Перезаписать мой голос",
        "menu_autostart": "Запуск вместе с Windows",
        "menu_language": "Язык",
        "menu_quit": "Выход",
        "enroll_title": "Aria — регистрация голоса",
        "enroll_intro": "Чтобы звуком управлял только ваш голос, мы один раз "
                        "запишем его.\nПрочитайте фразу ниже вслух, естественно.",
        "enroll_phrase": "\"{wake}, play the music. {wake}, volume five zero.\"",
        "enroll_start": "Начать запись",
        "enroll_listening": "Слушаю… говорите",
        "enroll_progress": "Образец {n}/{total} получен",
        "enroll_success": "Готово! Теперь звуком управляет только ваш голос.",
        "enroll_failed": "Не удалось чётко записать голос. Попробовать снова?",
        "enroll_retry": "Попробовать снова",
        "enroll_close": "Закрыть",
        "notify_locked": "Это не ваш голос — команда отклонена.",
    },
}

# Qo'shimcha kalitlar (overlay) — har bir tilga qo'shamiz
_EXTRA = {
    "uz": {"menu_overlay": "Ekran bildirishnomasi", "overlay_listening": "Tinglayapman…"},
    "en": {"menu_overlay": "On-screen overlay", "overlay_listening": "Listening…"},
    "es": {"menu_overlay": "Aviso en pantalla", "overlay_listening": "Escuchando…"},
    "ja": {"menu_overlay": "画面通知", "overlay_listening": "聞いています…"},
    "ru": {"menu_overlay": "Экранное уведомление", "overlay_listening": "Слушаю…"},
}
for _lang, _extra in _EXTRA.items():
    STRINGS[_lang].update(_extra)


# Til kodi -> chiroyli nom (til tanlagich uchun)
LANG_NAMES = {
    "uz": "O'zbekcha",
    "en": "English",
    "es": "Español",
    "ja": "日本語",
    "ru": "Русский",
}


class I18n:
    def __init__(self, lang: str = "en"):
        self.lang = lang if lang in STRINGS else "en"

    def set_lang(self, lang: str) -> None:
        if lang in STRINGS:
            self.lang = lang

    def t(self, key: str, **kwargs) -> str:
        text = STRINGS.get(self.lang, STRINGS["en"]).get(key) \
            or STRINGS["en"].get(key, key)
        return text.format(**kwargs) if kwargs else text
