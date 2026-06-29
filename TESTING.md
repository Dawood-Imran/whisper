# Testing Voice Codex Phase 1

This guide verifies the one-shot command, hotkey daemon, vocabulary corrections, and background service:

```text
preflight -> recording -> Deepgram Flux transcription -> vocabulary corrections -> clipboard/direct insertion
```

Phase 4 includes deterministic vocabulary corrections, user-level service management, and best-effort active cursor paste. It does not include fuzzy matching, silence detection, GUI, or auto-submit.

## Model Used

Default transcription settings:

```text
engine: deepgram-flux
endpoint: wss://api.deepgram.com/v2/listen
model: flux-general-en
encoding: linear16
sample_rate: 16000
channels: 1
chunk_ms: 80
api_key_env: DEEPGRAM_API_KEY
```

This follows `deepgram.md`: Flux requires `/v2/listen`, `flux-general-en` for English, and linear16 audio chunks. Do not use `/v1/listen` for Flux.

## 1. Create A Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

## 2. Configure Deepgram

Set your API key in the environment:

```bash
export DEEPGRAM_API_KEY="your_deepgram_api_key"
```

Or create a local `.env` file:

```bash
printf 'DEEPGRAM_API_KEY="your_deepgram_api_key"\n' > .env
```

Do not commit `.env` or paste the API key into logs.

## 3. Install Clipboard Support

On Wayland, install clipboard support if `wl-copy` is missing:

```bash
sudo apt install wl-clipboard
```

On X11, install clipboard and paste support if missing:

```bash
sudo apt install xclip xdotool
```

## 4. Run Preflight

```bash
voice-codex-preflight
```

Or without installed console scripts:

```bash
python -m voice_codex preflight
```

Expected output includes:

- Python version.
- Linux session type.
- Deepgram engine, model, endpoint, and API key status.
- Vocabulary term and correction counts.
- Python package readiness.
- Hotkey dependency readiness.
- System command readiness.
- Audio input devices.
- Clipboard backend.
- Insertion mode.

## 5. Test A Short Recording

Start with a short duration:

```bash
voice-codex-once --duration 3 --no-paste
```

Speak a simple phrase like:

```text
Dawood, test the Codex voice command.
```

Expected behavior:

1. A 3-second audio clip is recorded locally.
2. The linear16 audio is streamed to Deepgram Flux.
3. The transcript is printed in the terminal.
4. The transcript is copied to the clipboard if a supported clipboard tool exists.
5. Nothing is auto-submitted to Codex.

## 6. Test With Kept Audio

If transcription fails or seems wrong, keep the WAV file:

```bash
voice-codex-once --duration 5 --keep-audio --no-paste
```

This writes a file like:

```text
voice-codex-once-YYYYMMDD-HHMMSS.wav
```

Use this only for debugging. Phase 1 normally deletes temporary audio after transcription.

## 7. Test Focused Terminal Insertion

On X11 with `xclip` and `xdotool` installed:

```bash
voice-codex-once --duration 5
```

Expected behavior:

1. Text is copied to the clipboard.
2. On X11, the command tries to paste into the active window using `Ctrl+Shift+V`.
3. On Wayland, the command types the transcript into the active window using `ydotool`.
4. You manually review the inserted prompt.
5. You manually press Enter.

If your terminal uses `Ctrl+V` instead:

```bash
voice-codex-once --duration 5 --paste-shortcut ctrl+v
```

On Wayland, active insertion requires `ydotool` and `ydotoold`. If direct insertion is unavailable, manually paste the copied transcript into Codex CLI.

## 8. Optional Deepgram Settings

Use Flux multilingual only when needed:

```bash
voice-codex-once --model flux-general-multi --language-hint en --duration 5 --no-paste
```

Do not pass `--language-hint` with the default `flux-general-en` model.

If final Deepgram messages arrive slowly:

```bash
voice-codex-once --duration 5 --close-timeout 15 --no-paste
```

## 9. Configure Vocabulary Corrections

Create the default config directory:

```bash
mkdir -p ~/.config/voice-codex
```

Create vocabulary terms:

```bash
cat > ~/.config/voice-codex/vocabulary.txt <<'EOF'
Dawood
Codex
FastAPI
PostgreSQL
JWT
Deepgram
EOF
```

Create deterministic correction rules:

```bash
cat > ~/.config/voice-codex/corrections.toml <<'EOF'
[corrections]
"the wood" = "Dawood"
"da wood" = "Dawood"
"fast api" = "FastAPI"
"post gray sql" = "PostgreSQL"
"j w t" = "JWT"
"code x" = "Codex"
EOF
```

Run preflight:

```bash
voice-codex-preflight
```

Expected output should include nonzero correction counts if the file exists.

Disable corrections for comparison:

```bash
voice-codex-once --duration 5 --no-vocabulary --no-paste
```

Use custom files:

```bash
voice-codex-once \
  --vocab-file ./vocabulary.txt \
  --corrections-file ./corrections.toml \
  --duration 5 \
  --no-paste
```

## 10. Test The Phase 2 Daemon

Start the daemon in a terminal:

```bash
voice-codex-daemon
```

Or:

```bash
python -m voice_codex daemon
```

Default hotkey:

```text
F9
```

Expected behavior:

1. The daemon starts and logs the configured hotkey.
2. Pressing `F9` starts recording.
3. Pressing `F9` again stops recording.
4. The daemon sends audio to Deepgram Flux.
5. The transcript is copied or inserted.
6. The daemon returns to idle.
7. You manually review and press Enter in Codex.

Desktop notifications should appear for recording start, recording stop, transcribing, copied/inserted, and errors. Disable them with:

```bash
voice-codex-daemon --no-notify
```

Use a custom hotkey if needed:

```bash
voice-codex-daemon --hotkey '<ctrl>+<shift>+space'
```

Keep daemon audio for debugging:

```bash
voice-codex-daemon --keep-audio --audio-dir ./recordings
```

On Wayland, the desktop session may block global keyboard listeners. If the daemon starts but never receives the hotkey, keep using `voice-codex-once` while we add a desktop-specific trigger path in a later phase.

## 11. Test The Phase 4 Background Service

Install and start the user service:

```bash
voice-codex service install --enable --start
```

Make sure the service can read the API key:

```bash
mkdir -p ~/.config/voice-codex
printf 'DEEPGRAM_API_KEY="your_deepgram_api_key"\n' > ~/.config/voice-codex/env
```

Replace `your_deepgram_api_key` with the real key. A placeholder value will cause Deepgram `HTTP 401`.

Check status:

```bash
voice-codex service status
```

View logs:

```bash
voice-codex service logs --lines 120
```

Restart after changing code or config:

```bash
voice-codex service restart
```

Stop the background daemon:

```bash
voice-codex service stop
```

On Wayland, install active paste support:

```bash
sudo apt install ydotool ydotoold
```

Depending on your distribution, `ydotoold` must also be running and your user may need access to `/dev/uinput`. `ydotool` by itself is only the client; direct paste will not work until a ydotool socket exists at `YDOTOOL_SOCKET`, `/tmp/.ydotool_socket`, or `/run/user/<uid>/.ydotool_socket`.

On Ubuntu, the `ydotoold` package may install `/usr/bin/ydotoold` without installing a systemd unit. In that case, install the project-provided unit:

```bash
sudo cp "/home/tk-lpt-0427/Dawood Personal/whisper/systemd/ydotoold.service" /etc/systemd/system/ydotoold.service
sudo chmod 0644 /etc/systemd/system/ydotoold.service
sudo systemctl daemon-reload
sudo systemctl enable --now ydotoold.service
```

Run preflight after installing and starting `ydotoold`:

```bash
voice-codex-preflight
```

Expected insertion mode with `ydotool` and a running `ydotoold` socket:

```text
wayland-ydotool-type
```

## 12. Common Failure Modes

### Missing Python Packages

If preflight reports missing Python packages, reinstall the project:

```bash
python -m pip install -e .
```

If the daemon reports missing `pynput`, rerun the same install command.

### Missing Deepgram API Key

Set the key:

```bash
export DEEPGRAM_API_KEY="your_deepgram_api_key"
```

Then rerun:

```bash
voice-codex-preflight
```

### Missing Clipboard Tool

Wayland:

```bash
sudo apt install wl-clipboard
```

X11:

```bash
sudo apt install xclip xdotool
```

### Service Does Not Start

Check status and logs:

```bash
voice-codex service status
voice-codex service logs --lines 120
```

If the service cannot find your API key, make sure it is available from the service working directory through `.env` or exported into the user service environment.

### Wayland Does Not Paste Into Cursor

If preflight shows `clipboard-only`, install and configure `ydotool`. Clipboard copy still works without active paste.

### No Microphone Devices

Check system audio settings and run:

```bash
voice-codex-preflight
```

If multiple devices are listed, choose one:

```bash
voice-codex-once --input-device 3 --duration 5 --no-paste
```

### Network Or API Failure

Deepgram transcription requires outbound network access to:

```text
wss://api.deepgram.com/v2/listen
```

If the command fails during transcription, verify the API key, network access, and Deepgram account status.

### Bad Corrections File

If preflight reports a corrections parse error, check that the file has this shape:

```toml
[corrections]
"wrong phrase" = "CorrectPhrase"
```

## 13. Developer Checks

Run syntax and unit checks:

```bash
python -m compileall voice_codex tests
python -m unittest discover -s tests
python -m voice_codex daemon --help
python -m voice_codex service --help
```

If development dependencies are installed:

```bash
python -m pip install -e ".[dev]"
python -m pytest
```

## Success Criteria

Phase 1 is working when:

- `voice-codex-preflight` gives clear environment diagnostics.
- `voice-codex-once` records without crashing.
- `voice-codex-daemon` starts and listens for the configured hotkey.
- Deepgram Flux produces readable transcript text.
- Explicit vocabulary corrections are applied before copy/insert.
- The transcript is copied to the clipboard or inserted into the focused terminal.
- `voice-codex service start` can run the daemon in the background.
- The command does not auto-submit to Codex.
