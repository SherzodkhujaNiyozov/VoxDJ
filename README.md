<p align="center"><b>Aria</b> — control your PC audio with your voice. Like Jarvis, but for sound.</p>

---

**Aria** is an offline, privacy-first Windows tray app that lets you control your system audio by **voice**. By default it obeys **only your voice** — it learns your voiceprint the first time you open it, so a passer-by can't hijack your music. Flip one switch and anyone can control it.

No account. No database. No cloud. The internet is used **once**, to download the speech models.

## Features

- 🔒 **Owner-only by default** — voice biometrics (speaker verification) mean only *your* voice controls the audio. One checkbox (or say `everyone`) opens it up to everyone; say `private` to lock it back.
- 🎙️ **Voice commands** (always in English). Say the wake word together with the command, then:
  | Say | Action |
  |-----|--------|
  | `play` / `pause` / `stop` | play, pause, stop whatever is playing |
  | `skip` | next track / video |
  | `previous` | previous track / video |
  | `mute` / `unmute` | mute / unmute |
  | `louder` / `quieter` | volume ±10% |
  | `volume five zero` | set volume to **50%** (say the number digit-by-digit) |
  | `spotify five zero` | set **a specific app's** volume (see per-app below) |
  | `everyone` | switch to **allow anyone** to control |
  | `private` | switch back to **owner-only** mode |
  | `microphone` | switch to the **next microphone** (cycles through input devices) |

  > **Why digit-by-digit?** The offline speech model reliably hears `five zero` (=50) but often confuses `fifty`↔`fifteen`. So say each digit: `volume two zero` = 20%, `volume seven five` = 75%, `volume hundred` = 100%.
- 🎚️ **Per-app volume** — control one app's sound instead of the whole system. Put an app name **before** the command:
  - `aria spotify five zero` — set Spotify to 50%
  - `aria chrome mute` / `aria chrome unmute`
  - `aria music quieter` — Yandex Music / Spotify / any media app
  - `aria app five zero` — the app **currently playing** (say it after the beep, on its own)

  Recognized app words: **spotify, chrome, firefox, edge, youtube, telegram, music, app**. (Play/pause/skip stay global — Windows has no per-app transport key.)
- 🗣️ **Custom wake word** — choose between **Aria**, **Vox**, **Jarvis**, or type your own word in the tray. The wake word must be said in one breath with the command: *"Aria play."*, *"Jarvis volume five zero."* A short beep confirms it's listening; you then have ~8 s for follow-up commands. Toggle the wake word off in the tray to skip it entirely.
- 🎤 **Microphone selection** — pick your input device from the tray (Microphone submenu) or say `{wake} microphone` to cycle through devices by voice.
- 🤖 **Voice feedback** — a Jarvis-style spoken reply ("Volume fifty percent").
- 💬 **On-screen overlay** — a small corner notification shows each recognized command. Stays visible even when the audio is muted. Toggle it in the tray.
- 🌐 **5-language interface** — Uzbek, English, Spanish, Japanese, Russian.
- 🪟 Runs in the **system tray**, optional **start with Windows**.
- ⚡ **Fully offline**, lightweight, free. Works on any Windows PC.

## Install (from source)

Requires **Python 3.13** on Windows.

```powershell
# 1. Dependencies
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt

# 2. Download the offline speech models (one time, ~55 MB)
.venv\Scripts\python.exe download_models.py

# 3. Run
.venv\Scripts\python.exe -m aria
```

On first launch a small window asks you to read one sentence out loud — that's the voice enrollment. After that, Aria lives in your tray.

## Usage

1. Say the **wake word** attached to the command in one breath — e.g. *"Aria volume five zero."*, *"Aria play."* (a short beep confirms it heard the wake word).
2. After the beep you have ~8 seconds to give follow-up commands without repeating the wake word.
3. Prefer **`louder` / `quieter`** for everyday volume — they're the most reliable.
4. With the wake word off (tray), just say the command — *"pause"*, *"louder"*, *"mute"*.
5. Right-click the tray icon for settings: owner-only / everyone, wake word selection, microphone selection, voice feedback, on-screen overlay, language, re-enroll, start with Windows.

## Build a single .exe

```powershell
./build.ps1   # produces dist\Aria.exe
```

Place the `models\` folder next to the `.exe` (or run `download_models.py` once).

## Troubleshooting

- **"Modellar topilmadi"** → run `download_models.py` first.
- **Commands ignored** → if owner-only is on and it doesn't recognize you, lower the threshold or re-enroll from the tray. Make sure you're in a reasonably quiet room.
- **No microphone / wrong mic** → select your input device from the tray (Microphone submenu), or say `{wake} microphone` to cycle through devices.
- **Wake word never triggers** → say the wake word clearly, attached to the command (*"Aria play"*). Speak it crisply — the offline model needs a clear sound. You can also turn the wake word off in the tray.
- **Wrong volume / number misheard** → say the percentage **digit-by-digit** (`volume five zero` = 50, not `volume fifty`). For "next track" say **`skip`** (the model hears it more reliably than "next").

## Privacy

Everything stays on your machine. Audio is processed locally and never recorded to disk or sent anywhere. Your voiceprint is a small math vector stored at `%APPDATA%\Aria\voiceprint.json` — it cannot reconstruct your voice. See [SECURITY.md](SECURITY.md).

## Tech

Python · [Vosk](https://alphacephei.com/vosk/) (offline ASR + speaker x-vector) · pycaw (Core Audio) · pystray · pyttsx3 (offline TTS) · Tkinter.
