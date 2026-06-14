# Security & Privacy

Aria is built to be private by design.

## What stays on your machine

- **Audio is never stored.** The microphone stream is processed in memory by the local Vosk engine and discarded. Nothing is written to disk, and nothing is sent over the network.
- **No telemetry, no analytics, no accounts, no database.** Aria has no server side.
- **The only network access** is the one-time model download in `download_models.py` (over HTTPS from alphacephei.com). After that, the app runs fully offline. You can verify this — there are no other `urllib`/socket calls in the codebase.

## Your voiceprint

- Stored at `%APPDATA%\Aria\voiceprint.json` as a 128-dimension normalized vector (an *x-vector*).
- This vector is a one-way numeric fingerprint used only for cosine-similarity comparison. **It cannot be turned back into your voice or any audio.**
- Delete the file (or use **Re-enroll** in the tray) to reset it at any time.

## Settings

- `%APPDATA%\Aria\config.json` holds only preferences (language, thresholds, toggles). It is written **atomically** (temp file + rename) so a crash can't corrupt it, and all values are clamped to safe ranges on load.

## Model integrity

- Models are downloaded **only over HTTPS** — `download_models.py` refuses any non-`https://` URL.
- Each archive is extracted with a **zip-slip guard**: every entry is verified to stay inside the `models/` directory, so a tampered archive can't write files elsewhere on your system.
- `download_models.py` prints the SHA-256 of each downloaded archive. You can pin the expected hash in the `MODELS` list to guarantee the bytes never change between installs.

## Reporting

Found a security issue? Open a private report on the repository's Security tab, or email the maintainer. Please don't file public issues for vulnerabilities.
