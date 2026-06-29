# Voice Codex

Voice Codex is a Linux command-line prototype for speaking a prompt, transcribing it with Deepgram Flux, and inserting or copying the result for use in Codex CLI.

Phase 2 adds a foreground background-daemon workflow with a global toggle hotkey. The daemon records audio, streams it to Deepgram for transcription, and delivers text back to the focused terminal. Auto-submit remains disabled.

Phase 3 adds local vocabulary correction after Deepgram transcription. Correction rules are deterministic and user-controlled.

Phase 4 adds user-level background service commands and best-effort paste into the active cursor.

## Phase 1 Commands

- `voice-codex-preflight`
- `voice-codex-once`
- `voice-codex-daemon`
- `voice-codex service ...`

Default transcription model:

- Engine: `deepgram-flux`
- Endpoint: `wss://api.deepgram.com/v2/listen`
- Model: `flux-general-en`
- API key environment variable: `DEEPGRAM_API_KEY`
- Audio sent to Deepgram: `linear16`, `16000` Hz, mono

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

Corrections run after Deepgram transcription and before clipboard insertion.

## Daemon Usage

```bash
voice-codex-daemon
```

Default hotkey:

```text
F9
```

Press once to start recording and press again to stop, transcribe, and copy or insert the result. The daemon uses desktop notifications for recording, transcription, copied/inserted, and error states. On Wayland, global keyboard listeners may be blocked by the desktop session; use `voice-codex-once` as the fallback while validating the daemon.

## Background Service

Install and start the user service:

```bash
voice-codex service install --enable --start
```

For background service API keys, create:

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

On Wayland, active paste into the focused cursor requires `ydotool` and a running `ydotoold`. On Ubuntu these can be separate packages, and the `ydotoold` package may not ship a systemd service file. Without a running `ydotoold` socket, Voice Codex still copies the transcript to the clipboard.
