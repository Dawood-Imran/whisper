# Voice-to-Codex Linux Wrapper: Requirements and Implementation Plan

> Phase 1 update: transcription now uses Deepgram Flux via the `/v2/listen`
> WebSocket API with `model=flux-general-en`, `encoding=linear16`, and
> `sample_rate=16000`. The earlier local `faster-whisper` path is no longer the
> active Phase 1 implementation.

## 1. Goal

Build a Linux background service that lets the user press a keyboard shortcut, such as `Ctrl+R`, while the cursor is inside the Codex CLI terminal. The service records the user's voice, transcribes it locally using an open-source speech-to-text model, applies custom vocabulary correction or biasing, and inserts the final text directly into the active Codex CLI prompt.

The user should not need to manually copy or paste anything.

## 2. Target User Flow

1. User starts Codex CLI in a terminal:

   ```bash
   codex
   ```

2. User keeps the cursor focused inside the Codex CLI input area.

3. User presses a global shortcut, for example:

   ```text
   Ctrl+R
   ```

4. Background daemon starts recording microphone audio.

5. User speaks a prompt, for example:

   ```text
   Dawood, refactor the auth middleware and add tests for token expiry.
   ```

6. User presses the same shortcut again, or the system stops after detecting silence.

7. Audio is transcribed locally.

8. Custom vocabulary handling corrects terms like:

   ```text
   Dawood
   Codex
   FastAPI
   PostgreSQL
   JWT
   ```

9. Final text is typed into the currently focused Codex CLI window.

10. User reviews the prompt and manually presses Enter.

Auto-submit should be optional but disabled by default.

## 3. Main Design Decision

The system should be implemented as a background daemon instead of a one-shot command.

### Reason

The user wants a shortcut such as `Ctrl+R` to work while they are already inside the Codex terminal. A normal command like `voice-codex` requires switching terminals or launching another process manually. A daemon can keep listening for the shortcut in the background and trigger recording without interrupting the terminal workflow.

## 4. Recommended Architecture

```text
voice-codexd daemon
        |
        | listens for global hotkey
        v
Ctrl+R pressed
        |
        v
record microphone audio
        |
        v
run local speech-to-text model
        |
        v
apply vocabulary bias / correction rules
        |
        v
insert final text into active window
        |
        v
Codex CLI receives the prompt
```

## 5. Components

### 5.1 Background Daemon

A Python process named:

```text
voice-codexd
```

Responsibilities:

- Start automatically when the user logs in.
- Listen for a global hotkey.
- Manage recording state.
- Run transcription.
- Apply custom vocabulary corrections.
- Type the final text into the active window.
- Write logs for debugging.

### 5.2 Command-Line Control Tool

A small command named:

```text
voice-codexctl
```

Responsibilities:

- Start the daemon.
- Stop the daemon.
- Restart the daemon.
- Show daemon status.
- Test microphone recording.
- Test transcription.
- Add custom vocabulary words.
- List custom vocabulary words.

Example commands:

```bash
voice-codexctl status
voice-codexctl test-mic
voice-codexctl test-transcribe
voice-codexctl vocab add Dawood
voice-codexctl vocab add FastAPI
voice-codexctl vocab list
```

### 5.3 Configuration File

Config path:

```text
~/.config/voice-codex/config.toml
```

Example:

```toml
[hotkey]
shortcut = "<ctrl>+r"
mode = "toggle"

[recording]
sample_rate = 16000
channels = 1
max_duration_seconds = 45
silence_stop_enabled = true
silence_seconds = 1.2

[transcription]
engine = "faster-whisper"
model = "base.en"
device = "cpu"
compute_type = "int8"
language = "en"

[insertion]
backend = "auto"
auto_submit = false
paste_method = "typing"

[vocabulary]
enabled = true
vocab_file = "~/.config/voice-codex/vocabulary.txt"
corrections_file = "~/.config/voice-codex/corrections.toml"

[logging]
level = "info"
file = "~/.local/state/voice-codex/voice-codexd.log"
```

### 5.4 Vocabulary File

Path:

```text
~/.config/voice-codex/vocabulary.txt
```

Example:

```text
Dawood
Codex
FastAPI
PostgreSQL
JWT
Next.js
Supabase
LangChain
OpenAI
whisper.cpp
faster-whisper
```

### 5.5 Correction Rules File

Path:

```text
~/.config/voice-codex/corrections.toml
```

Example:

```toml
[corrections]
"the wood" = "Dawood"
"da wood" = "Dawood"
"fast api" = "FastAPI"
"post gray sql" = "PostgreSQL"
"postgress" = "PostgreSQL"
"j w t" = "JWT"
"open ai" = "OpenAI"
"co decks" = "Codex"
"code x" = "Codex"
```

## 6. Speech-to-Text Engine

### Recommended First Engine: faster-whisper

Use `faster-whisper` for the first Python implementation.

Reasons:

- Python-native integration is simple.
- It runs Whisper models locally.
- It uses CTranslate2 for faster inference.
- It supports CPU execution with quantization.
- It can use `initial_prompt` to bias transcription toward custom words.

Example transcription call:

```python
segments, info = model.transcribe(
    audio_path,
    language="en",
    beam_size=5,
    vad_filter=True,
    initial_prompt="Important words: Dawood, Codex, FastAPI, PostgreSQL, JWT, Supabase."
)
```

### Alternative Engine: whisper.cpp

`whisper.cpp` should be considered later if the user wants:

- Lower dependency overhead.
- Better native Linux packaging.
- Better performance on some systems.
- A non-Python transcription backend.

For version 1, use `faster-whisper` unless performance is poor.

## 7. Custom Vocabulary Strategy

Whisper-style models do not have a simple guaranteed dictionary mode. The system should use a layered strategy.

### 7.1 Layer 1: Initial Prompt Biasing

Before transcription, build an initial prompt from the vocabulary file.

Example:

```text
Important project vocabulary and names: Dawood, Codex, FastAPI, PostgreSQL, JWT, Supabase, Next.js.
```

This helps the model prefer these words during decoding.

Limitations:

- It improves probability but does not guarantee exact spelling.
- It works better for repeated domain words than for completely unfamiliar names.
- Very long vocabulary lists may reduce usefulness.

### 7.2 Layer 2: Post-Transcription Corrections

After transcription, apply deterministic corrections.

Example:

```text
"the wood" -> "Dawood"
"fast api" -> "FastAPI"
"postgress" -> "PostgreSQL"
```

This is required because initial prompt bias alone will not always fix names or technical terms.

### 7.3 Layer 3: Fuzzy Matching

Optionally add fuzzy matching for near-miss words.

Example:

```text
Dawud -> Dawood
Dawoodh -> Dawood
Postgres SQL -> PostgreSQL
```

This should be conservative. Over-aggressive fuzzy correction can damage normal text.

### 7.4 Layer 4: User Review

By default, the daemon should insert the text but should not press Enter. The user should review the transcription before submitting it to Codex.

## 8. Recording Behavior

### Version 1: Toggle Recording

Use one shortcut:

```text
Ctrl+R
```

Behavior:

```text
First Ctrl+R  -> start recording
Second Ctrl+R -> stop recording, transcribe, insert
```

This is the most predictable behavior.

### Version 2: Silence Detection

Later, add automatic stop after silence.

Example behavior:

```text
Ctrl+R -> start recording
user speaks
1.2 seconds of silence -> stop automatically
transcribe and insert
```

Silence detection is useful, but it adds complexity. It should not be required in version 1.

## 9. Text Insertion Strategy

The final text must appear in the focused Codex CLI window.

There are three possible methods.

### 9.1 X11 Method

If the Linux session is X11, use:

```text
xdotool
```

Flow:

1. Copy transcription to clipboard.
2. Simulate `Ctrl+Shift+V` or `Ctrl+V`, depending on terminal.

Potential issue:

- Terminal paste shortcut is often `Ctrl+Shift+V`, not `Ctrl+V`.

Recommended config:

```toml
[insertion]
backend = "x11"
paste_shortcut = "ctrl+shift+v"
```

### 9.2 Wayland Method

If the Linux session is Wayland, use:

```text
ydotool + ydotoold
```

Reason:

Wayland restricts global key injection for security. `ydotool` uses Linux `uinput` to emulate a virtual input device and can work across X11 and Wayland when configured correctly.

Requirements:

- `ydotool` installed.
- `ydotoold` running in the background.
- User may need permission to access `/dev/uinput`.

### 9.3 Fallback Method

If direct insertion fails:

1. Copy transcription to clipboard.
2. Show notification:

   ```text
   Voice prompt copied. Paste manually into Codex.
   ```

This fallback prevents data loss.

## 10. Hotkey Strategy

### Important Conflict

`Ctrl+R` is commonly used in shells for reverse history search. Inside many terminals, `Ctrl+R` already has meaning.

Because the daemon listens globally, it can intercept `Ctrl+R`, but this may conflict with normal terminal usage.

### Recommended Default

Use a less risky default:

```text
Ctrl+Alt+R
```

Allow the user to change it to:

```text
Ctrl+R
```

Config:

```toml
[hotkey]
shortcut = "<ctrl>+<alt>+r"
```

If the user strongly prefers `Ctrl+R`, support it, but document the shell conflict.

## 11. Background Service Requirement

The daemon must keep running in the background.

Use a user-level `systemd` service.

Service file path:

```text
~/.config/systemd/user/voice-codexd.service
```

Example:

```ini
[Unit]
Description=Voice-to-Codex background daemon
After=graphical-session.target sound.target

[Service]
Type=simple
ExecStart=%h/.local/bin/voice-codexd
Restart=on-failure
RestartSec=2
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=default.target
```

Enable it:

```bash
systemctl --user daemon-reload
systemctl --user enable --now voice-codexd.service
```

Check status:

```bash
systemctl --user status voice-codexd.service
```

View logs:

```bash
journalctl --user -u voice-codexd.service -f
```

## 12. Dependencies

### System Packages

For Debian/Ubuntu-based systems:

```bash
sudo apt update
sudo apt install -y \
  python3 \
  python3-venv \
  python3-pip \
  portaudio19-dev \
  ffmpeg \
  xclip \
  xdotool
```

For Wayland support:

```bash
sudo apt install -y ydotool wl-clipboard
```

Depending on the distribution, `ydotoold` may need additional setup.

### Python Packages

```text
faster-whisper
sounddevice
numpy
pynput
pyperclip
tomli; python_version < "3.11"
tomli-w
rapidfuzz
```

Optional:

```text
webrtcvad
```

## 13. Proposed Project Structure

```text
voice-codex/
├── pyproject.toml
├── README.md
├── requirements.txt
├── voice_codex/
│   ├── __init__.py
│   ├── daemon.py
│   ├── config.py
│   ├── recorder.py
│   ├── transcriber.py
│   ├── vocabulary.py
│   ├── inserter.py
│   ├── hotkeys.py
│   ├── notify.py
│   └── cli.py
├── scripts/
│   ├── install.sh
│   └── uninstall.sh
└── systemd/
    └── voice-codexd.service
```

## 14. Implementation Phases

### Phase 1: Minimal Working Prototype

Goal: prove the core idea.

Features:

- Fixed-duration recording.
- Local transcription with `faster-whisper`.
- Copy result to clipboard.
- Paste into focused terminal using `xdotool`.

No daemon yet.

Command:

```bash
voice-codex-once
```

Success condition:

- User runs the command.
- Speaks for 10 seconds.
- Text appears in Codex CLI.

### Phase 2: Background Daemon

Goal: support hotkey workflow.

Features:

- `voice-codexd` runs in background.
- Global hotkey starts/stops recording.
- Text is inserted into focused window.
- Logs are written.

Success condition:

- User presses shortcut while Codex CLI is focused.
- Speaks.
- Presses shortcut again.
- Text appears inside Codex.

### Phase 3: Vocabulary Support

Goal: improve recognition of names and technical terms.

Features:

- `vocabulary.txt` support.
- `corrections.toml` support.
- Initial prompt biasing.
- Deterministic post-processing corrections.

Success condition:

- User says "Dawood".
- Transcription inserts "Dawood", not "the wood" or "Da wood".

### Phase 4: Wayland Compatibility

Goal: work beyond X11.

Features:

- Detect session type using `XDG_SESSION_TYPE`.
- Use `xdotool` on X11.
- Use `ydotool` on Wayland where available.
- Fall back to clipboard-only mode if injection fails.

Success condition:

- The system works on X11.
- On Wayland, the system either inserts text or safely copies it and notifies the user.

### Phase 5: Silence Detection

Goal: make recording more natural.

Features:

- Stop recording after configurable silence duration.
- Keep manual toggle as fallback.

Success condition:

- User presses shortcut once.
- Speaks.
- System stops after silence and inserts text.

## 15. Acceptance Criteria

The project is considered successful when:

1. The daemon starts automatically after login.
2. The configured hotkey triggers recording while Codex CLI is focused.
3. Transcription is local and does not require sending audio to a cloud API.
4. Custom words like `Dawood` can be added by the user.
5. The final transcribed text is inserted into Codex CLI without manual copy/paste.
6. The system does not auto-submit by default.
7. The system has a fallback when direct insertion fails.
8. Logs are available for debugging.
9. The user can enable, disable, or restart the daemon using `systemctl --user`.

## 16. Non-Goals

The first version should not attempt to:

- Build a GUI.
- Support all Linux desktop environments perfectly.
- Fine-tune Whisper.
- Guarantee perfect spelling for all custom vocabulary.
- Automatically submit prompts to Codex by default.
- Record continuously without explicit user activation.
- Replace ChatGPT voice mode.

## 17. Risks and Mitigations

### Risk: `Ctrl+R` conflicts with shell reverse search

Mitigation:

- Default to `Ctrl+Alt+R`.
- Allow custom hotkey configuration.

### Risk: Wayland blocks keyboard injection

Mitigation:

- Use `ydotool` where possible.
- Provide clipboard-only fallback.
- Document setup requirements.

### Risk: Whisper mishears custom names

Mitigation:

- Use initial prompt biasing.
- Add deterministic correction rules.
- Keep manual review before submission.

### Risk: First transcription is slow

Mitigation:

- Load the model once when daemon starts.
- Keep model in memory.
- Use `base.en` or `small.en` depending on system performance.

### Risk: Hotkey listener needs permissions

Mitigation:

- Document desktop-specific requirements.
- Provide test command:

  ```bash
  voice-codexctl test-hotkey
  ```

### Risk: Accidental recording

Mitigation:

- Play a short beep or show notification when recording starts/stops.
- Add maximum recording duration.
- Add visible log/status indicator.

## 18. Security and Privacy Requirements

1. Audio must be processed locally by default.
2. No audio should be sent to external APIs unless the user explicitly enables that later.
3. Temporary audio files should be deleted after transcription.
4. Logs should not store raw audio.
5. Logs should avoid storing full prompt text by default.
6. The daemon should only record after the configured hotkey is pressed.
7. The daemon should not continuously record in the background.

## 19. Recommended Defaults

```toml
[hotkey]
shortcut = "<ctrl>+<alt>+r"
mode = "toggle"

[transcription]
engine = "faster-whisper"
model = "base.en"
device = "cpu"
compute_type = "int8"
language = "en"

[insertion]
backend = "auto"
auto_submit = false

[vocabulary]
enabled = true
```

## 20. Useful Implementation Notes

### Detect X11 or Wayland

```python
import os

session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()

if session_type == "x11":
    backend = "xdotool"
elif session_type == "wayland":
    backend = "ydotool"
else:
    backend = "clipboard-only"
```

### Build Initial Prompt from Vocabulary

```python
from pathlib import Path

vocab_path = Path.home() / ".config/voice-codex/vocabulary.txt"
words = [line.strip() for line in vocab_path.read_text().splitlines() if line.strip()]
initial_prompt = "Important vocabulary: " + ", ".join(words[:50]) + "."
```

### Conservative Correction Example

```python
corrections = {
    "the wood": "Dawood",
    "da wood": "Dawood",
    "fast api": "FastAPI",
    "postgress": "PostgreSQL",
}

text_lower = text.lower()
for wrong, correct in corrections.items():
    text_lower = text_lower.replace(wrong, correct)
```

Production code should preserve capitalization more carefully than this simple example.

## 21. Suggested First Milestone

Do not start with the full daemon.

Start with this sequence:

1. Build `voice-codex-once`.
2. Confirm recording works.
3. Confirm transcription works.
4. Confirm insertion into Codex works.
5. Add vocabulary correction.
6. Then convert it into `voice-codexd` background daemon.

This avoids debugging microphone, transcription, hotkeys, and systemd all at once.

## 22. Final Recommendation

This is worth building if the user spends significant time in Codex CLI and wants a terminal-native voice workflow. It should be implemented as a small daemon, not a large application.

The best first version is:

```text
Ctrl+Alt+R -> start recording
Ctrl+Alt+R -> stop recording
local faster-whisper transcription
custom vocabulary prompt + corrections
insert text into Codex CLI
manual Enter by user
```

Only after this works reliably should the project add silence detection, Wayland polish, auto-submit, or GUI features.

## 23. References

- faster-whisper: https://github.com/SYSTRAN/faster-whisper
- whisper.cpp: https://github.com/ggml-org/whisper.cpp
- pynput global hotkey documentation: https://pynput.readthedocs.io/en/latest/keyboard-usage.html
- ydotool: https://github.com/ReimuNotMoe/ydotool
- OpenAI Whisper prompting guide: https://developers.openai.com/cookbook/examples/whisper_prompting_guide
