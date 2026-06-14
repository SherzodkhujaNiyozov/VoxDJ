<h1 align="center">🎙️ Aria</h1>
<p align="center"><b>Control your PC's audio with your voice.</b> Like Jarvis — but just for sound.</p>
<p align="center">
  <i>Offline · Privacy-first · Owner-only by voice · Windows tray app</i>
</p>

---

**Aria** lets you play/pause music, set the volume, mute, switch tracks and control individual apps **just by speaking** — no hands, no hotkeys. By default it obeys **only your voice**: it learns your voiceprint the first time you open it, so a passer-by can't hijack your music. Flip one switch and anyone can control it.

Everything runs **on your machine**. No account, no database, no cloud. The internet is used **once**, to download the speech models.

## ✨ Features

- 🔒 **Owner-only by default** — voice biometrics (speaker verification) mean only *your* voice controls the audio. One click (or the spoken command `everyone`) opens it to anyone.
- 🗣️ **Voice commands**, always in English, behind a wake word you choose.
- 🎚️ **System & per-app volume** — set the whole system or just Spotify/Chrome/etc.
- 🎛️ **Live device handling** — plug in headphones and Aria follows the new default output; switch microphones from the tray or by voice, in real time.
- 🤖 **Jarvis-style spoken feedback** and a 💬 **on-screen overlay** for every command (handy when muted).
- 🌐 **5-language interface** — Uzbek, English, Spanish, Japanese, Russian. (Commands stay English.)
- 🪟 **System tray** app, optional **start with Windows**.
- ⚡ **Fully offline**, lightweight, free, no telemetry.

## 🎤 Voice commands

Say your **wake word** (default **"Aria"**) attached to the command, in one breath — e.g. *"Aria, play."* A short beep confirms it heard you, and you then have ~8 seconds to give follow-up commands without repeating the wake word.

| Say | Action |
|-----|--------|
| `play` · `pause` · `stop` | play / pause / stop |
| `skip` | next track |
| `previous` | previous track |
| `mute` · `unmute` | mute / unmute |
| `louder` · `quieter` | volume ±10% |
| `volume five zero` | set volume to **50%** (digits, see note) |
| `<app> …` | control a single app (see below) |
| `microphone` | switch to the next microphone |
| `everyone` · `private` | allow anyone / owner-only |

> **Why digits?** The offline model reliably hears `five zero` (=50) but confuses `fifty`↔`fifteen`. So say each digit: `volume two zero` = 20%, `volume seven five` = 75%, `volume hundred` = 100%.

### 🎚️ Per-app volume

Put an app name **before** the command:

- `Aria spotify five zero` — set Spotify to 50%
- `Aria chrome mute` / `Aria chrome unmute`
- `Aria music quieter` — any media app (Spotify / Yandex Music / AIMP / …)
- `Aria app five zero` — whatever is **currently playing the loudest**

Recognized app words: **spotify, chrome, firefox, edge, youtube, telegram, music, app**. (Play/skip stay global — Windows has no per-app transport key.)

## ⚙️ Settings (tray menu)

Right-click the tray icon:

- **Owner only / Anyone can control** — the security switch.
- **Wake word** — pick **Aria**, **Vox**, **Jarvis**, or type your **own** word.
- **Require wake word** — turn the wake word off to react to bare commands.
- **Microphone** — opens a window to **select the active mic** (●) and **hide** mics you don't use (☑/☐). Stays open so you can adjust several; **⟳ Refresh** re-scans for newly plugged devices.
- **Voice feedback** / **On-screen overlay** — toggle the spoken reply and the corner notification.
- **Language** — switch the interface language.
- **Re-enroll my voice** — record your voiceprint again (do this on the mic you actually use).
- **Start with Windows** — autostart via the per-user registry key (no admin needed).

## 📦 Install (from source)

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

## 🏗️ Build a single .exe

```powershell
./build.ps1     # produces dist\Aria.exe
```

Place the `models\` folder next to the `.exe` (or run `download_models.py` once).

## 🩺 Troubleshooting

- **"Modellar topilmadi" / models not found** → run `download_models.py` first.
- **It doesn't recognize me in owner-only mode** → **Re-enroll** from the tray, **on the microphone you actually use**. Voiceprints don't transfer well between different mics (e.g. laptop mic vs. AirPods). Speak the whole sentence clearly for ~8 s so it captures enough samples.
- **Wrong microphone / new headset not listed** → open **Microphone** in the tray and hit **⟳ Refresh**, or say `Aria microphone` to cycle. Hide mics you never use so they're skipped.
- **Volume command changed nothing** → Aria targets the *current* default output; if you just unplugged headphones it follows the speakers automatically. Check the right device is the Windows default.
- **Wake word never triggers** → say it crisply, attached to the command (*"Aria play"*). Custom wake words must be ordinary English words the offline model knows (e.g. *computer*, *friday*) — very rare or non-English words may not be heard. You can also turn the wake word off in the tray.
- **Numbers misheard** → say the percentage **digit-by-digit** (`volume five zero` = 50). For "next track" say **`skip`**.

## 🔐 Privacy & security

Audio is processed locally and **never recorded to disk or sent anywhere**. Your voiceprint is a one-way math vector at `%APPDATA%\Aria\voiceprint.json` — it can't reconstruct your voice. Model downloads are HTTPS-only and extracted with a zip-slip guard. See **[SECURITY.md](SECURITY.md)** for the full picture.

## 🧠 How it works

| Concern | Tech |
|---------|------|
| Offline speech-to-text **and** speaker x-vector | [Vosk](https://alphacephei.com/vosk/) (`small-en-us` + `spk` models) |
| System & per-app volume | [pycaw](https://github.com/AndreMiras/pycaw) (Windows Core Audio) |
| Media keys (play/skip/…) | `ctypes` virtual-key events |
| Microphone capture | `sounddevice` (native-rate, resampled to 16 kHz) |
| Tray icon & menu | [pystray](https://github.com/moses-palmer/pystray) + Pillow |
| Spoken feedback | `pyttsx3` (Windows SAPI, offline) |
| Overlay & dialogs | Tkinter |

A constrained Vosk grammar (only the command words) keeps recognition accurate; speaker identity is a 128-dim x-vector compared by cosine similarity against your stored voiceprint.

## 📄 License

Personal / portfolio project. Free to use and learn from.
