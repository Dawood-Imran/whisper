# Voice Codex

Voice Codex is a Linux voice-to-text helper for Codex CLI. Press a hotkey, speak a prompt, press the hotkey again, and the app transcribes your speech with local `faster-whisper`, applies optional vocabulary corrections, then copies or inserts the text into the active window.

It does not auto-submit prompts. You review the inserted text and press Enter yourself.

## What It Uses

- Default transcription engine: `faster-whisper`
- Default model: `small.en`
- Recommended lower-latency model: `base.en`
- CPU mode: `device=cpu`, `compute_type=int8`, `cpu_threads=0`
- Default hotkey: `Ctrl+Alt+Space`
- Default recording limit: `45s`
- Clipboard: `wl-copy` on Wayland, `xclip`/`xsel` on X11
- Direct insertion: `ydotool` on Wayland, `xdotool` on X11

The daemon loads the speech model once at startup and reuses it for each recording. If you use `voice-codex-once`, the model loads for that one process.

## 1. Clone The Project

```bash
git clone git@github.com:Dawood-Imran/whisper.git
cd whisper
```

Or with HTTPS:

```bash
git clone https://github.com/Dawood-Imran/whisper.git
cd whisper
```

## 2. Install System Packages

Ubuntu/Debian baseline packages:

```bash
sudo apt update
sudo apt install -y \
  python3-venv \
  python3-pip \
  python3-dev \
  build-essential \
  portaudio19-dev \
  ffmpeg \
  libnotify-bin
```

For Wayland, install clipboard and direct-insertion tools:

```bash
sudo apt install -y wl-clipboard ydotool
```

For X11, install clipboard and paste tools:

```bash
sudo apt install -y xclip xdotool
```

## 3. Set Up Python

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

The first `faster-whisper` run may download the selected model from Hugging Face. `small.en` is more accurate but slower; `base.en` is a better latency/accuracy starting point on CPU.

## 4. Configure Wayland Direct Insertion

On Wayland, `ydotool` needs a running `ydotoold` daemon. Some distributions install `ydotool` but do not provide a systemd service.

Check whether a service already exists:

```bash
systemctl status ydotoold.service --no-pager
```

If it does not exist, install the service file from this repo. This command replaces the development username in the file with your current Linux username:

```bash
sed "s/tk-lpt-0427/$USER/g" systemd/ydotoold.service > /tmp/ydotoold.service
sudo install -m 0644 /tmp/ydotoold.service /etc/systemd/system/ydotoold.service
sudo systemctl daemon-reload
sudo systemctl enable --now ydotoold.service
```

Verify the socket is available to your user:

```bash
ls -l /tmp/.ydotool_socket
```

Expected shape:

```text
srw-rw---- 1 root your-user ... /tmp/.ydotool_socket
```

If direct insertion is not available, Voice Codex still copies the transcript to the clipboard.

## 5. Run Preflight

```bash
voice-codex-preflight
```

Or:

```bash
python -m voice_codex preflight
```

Expected result should show:

- `Transcription engine: faster-whisper`
- `faster_whisper: ok`
- detected microphone devices
- `Clipboard backend: wl-copy` on Wayland or `xclip`/`xsel` on X11
- `Insertion mode: wayland-ydotool-type`, `x11-paste`, or `clipboard-only`

## 6. Test One Recording

Start with a short no-paste test:

```bash
voice-codex-once --duration 5 --model base.en --no-paste
```

Expected behavior:

1. Audio records for 5 seconds.
2. `faster-whisper` transcribes the WAV file.
3. The transcript prints in the terminal.
4. The transcript is copied if a clipboard backend is available.
5. Nothing is submitted to Codex automatically.

Keep the WAV file for debugging:

```bash
voice-codex-once --duration 5 --model base.en --keep-audio --no-paste
```

## 7. Run The Foreground Daemon

```bash
voice-codex-daemon --model base.en
```

Default hotkey:

```text
Ctrl+Alt+Space
```

Press once to start recording. Press again to stop, transcribe, and insert/copy the text.

Use a different hotkey:

```bash
voice-codex-daemon --model base.en --hotkey '<ctrl>+<alt>+r'
```

Disable desktop notifications:

```bash
voice-codex-daemon --model base.en --no-notify
```

## 8. Run As A Background Service

Install, enable, and start the user service from the project directory:

```bash
voice-codex service install \
  --working-directory "$PWD" \
  --enable \
  --start \
  -- \
  --model base.en \
  --hotkey '<ctrl>+<alt>+<space>'
```

Control the service:

```bash
voice-codex service status
voice-codex service logs --lines 80
voice-codex service restart
voice-codex service stop
```

The service file is written to:

```text
~/.config/systemd/user/voice-codexd.service
```

The model loads once when the service starts. Logs should show one startup load:

```text
Loading faster-whisper model base.en on cpu with compute_type=int8.
faster-whisper model loaded.
```

Recording logs then show per-recording transcription timing:

```text
Processing recording with faster-whisper.
Transcribed ... chars from ... segments in ...s.
```

## 9. Model Choices

Use `base.en` for the first real latency test:

```bash
voice-codex service install --working-directory "$PWD" --enable --start -- --model base.en
voice-codex service restart
```

Use `tiny.en` if latency is still too high and lower accuracy is acceptable:

```bash
voice-codex service install --working-directory "$PWD" --enable --start -- --model tiny.en
voice-codex service restart
```

Use `small.en` when accuracy matters more than latency:

```bash
voice-codex service install --working-directory "$PWD" --enable --start -- --model small.en
voice-codex service restart
```

## 10. Vocabulary Corrections

Default files:

```text
~/.config/voice-codex/vocabulary.txt
~/.config/voice-codex/corrections.toml
```

Create the directory:

```bash
mkdir -p ~/.config/voice-codex
```

Example `corrections.toml`:

```toml
[corrections]
"the wood" = "Dawood"
"da wood" = "Dawood"
"fast api" = "FastAPI"
"j w t" = "JWT"
"code x" = "Codex"
```

Corrections run after transcription and before clipboard insertion.

Disable vocabulary corrections:

```bash
voice-codex-daemon --no-vocabulary
```

## 11. Optional Deepgram Backend

The default engine is local `faster-whisper` and does not need an API key.

If you intentionally use Deepgram:

```bash
export DEEPGRAM_API_KEY="your_deepgram_api_key"
voice-codex-once --engine deepgram-flux --model flux-general-en --duration 5 --no-paste
```

For the background service, store the key in:

```bash
mkdir -p ~/.config/voice-codex
printf 'DEEPGRAM_API_KEY="your_deepgram_api_key"\n' > ~/.config/voice-codex/env
```

Do not commit `.env` files or API keys.

## 12. Troubleshooting

### Hotkey Does Not Trigger

Wayland may block global keyboard listeners in some desktop sessions. First check logs:

```bash
voice-codex service logs --lines 120
```

Then test the one-shot command:

```bash
voice-codex-once --duration 5 --model base.en --no-paste
```

If one-shot works but the daemon hotkey does not, try another hotkey:

```bash
voice-codex service install --working-directory "$PWD" --enable --start -- --model base.en --hotkey '<ctrl>+<alt>+r'
voice-codex service restart
```

### Text Copies But Does Not Insert

Run:

```bash
voice-codex-preflight
voice-codex service logs --lines 120
```

On Wayland, confirm `ydotoold` is running and the socket is writable:

```bash
systemctl status ydotoold.service --no-pager
ls -l /tmp/.ydotool_socket
```

### Latency Is Too High

Check the timing line:

```text
Transcribed ... in ...s.
```

Most latency comes from transcription duration and model size. Try:

```bash
voice-codex service install --working-directory "$PWD" --enable --start -- --model tiny.en
voice-codex service restart
```

Also keep recordings short. A 20-second recording will take longer than a 5-second recording.

### Missing Microphone

Run:

```bash
voice-codex-preflight
```

If multiple devices are listed, choose one:

```bash
voice-codex-once --input-device 3 --duration 5 --model base.en --no-paste
```

### Model Download Fails

The first `faster-whisper` run may need network access to download the selected model. Retry when network access is available, or pre-load the model once:

```bash
python - <<'PY'
from voice_codex.transcriber import warm_up_transcriber
warm_up_transcriber(model_name="base.en")
print("model loaded")
PY
```

## Developer Checks

```bash
python -m compileall voice_codex tests
python -m unittest discover -s tests
python -m voice_codex daemon --help
python -m voice_codex service --help
```
