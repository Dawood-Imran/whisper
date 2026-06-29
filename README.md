# Voice Codex

Voice Codex is a Linux command-line prototype for speaking a prompt, transcribing it locally with faster-whisper, and inserting or copying the result for use in Codex CLI.

Phase 2 adds a foreground background-daemon workflow with a global toggle hotkey. The daemon records audio, transcribes it, and delivers text back to the focused terminal. Auto-submit remains disabled.

Phase 3 adds local vocabulary correction after transcription. Correction rules are deterministic and user-controlled.

Phase 4 adds user-level background service commands and best-effort paste into the active cursor.

Phase 5 switches the default transcription engine from Deepgram Flux to local faster-whisper.

## Phase 1 Commands

- `voice-codex-preflight`
- `voice-codex-once`
- `voice-codex-daemon`
- `voice-codex service ...`

Default transcription model:

- Engine: `faster-whisper`
- Model: `small.en`
- Device: `cpu`
- Compute type: `int8`
- CPU threads: `0` (all cores)
- Beam size: `1`
- Language: `en`
- VAD filter: enabled

See `TESTING.md` for setup and verification steps.

## Vocabulary Corrections

Default files:

```text
~/.config/voice-codex/vocabulary.txt
~/.config/voice-codex/corrections.toml
```

Example `corrections.toml`:

```toml
[corrections]
"the wood" = "Dawood"
"fast api" = "FastAPI"
"j w t" = "JWT"
"code x" = "Codex"
```

Corrections run after transcription and before clipboard insertion.

## Daemon Usage

```bash
voice-codex-daemon
```

Default hotkey:

```text
Ctrl+Alt+Space
```

Press once to start recording and press again to stop, transcribe, and copy or insert the result. The daemon uses desktop notifications for recording, transcription, copied/inserted, and error states. On Wayland, global keyboard listeners may be blocked by the desktop session; use `voice-codex-once` as the fallback while validating the daemon.

## Background Service

Install and start the user service:

```bash
voice-codex service install --enable --start
```

The default faster-whisper engine does not require an API key. If you intentionally run Deepgram with `--engine deepgram-flux`, create:

```bash
mkdir -p ~/.config/voice-codex
printf 'DEEPGRAM_API_KEY="your_deepgram_api_key"\n' > ~/.config/voice-codex/env
```

Replace `your_deepgram_api_key` with the real key. A placeholder value will cause Deepgram `HTTP 401`.

Control it:

```bash
voice-codex service status
voice-codex service logs
voice-codex service restart
voice-codex service stop
```

The service file is written to:

```text
~/.config/systemd/user/voice-codexd.service
```

On Wayland, active insertion into the focused cursor requires `ydotool` and a running `ydotoold`. On Ubuntu these can be separate packages, and the `ydotoold` package may not ship a systemd service file. Without a running `ydotoold` socket, Voice Codex still copies the transcript to the clipboard.
