# Voice Codex

Voice Codex is a Linux command-line prototype for speaking a prompt, transcribing it with Deepgram Flux, and inserting or copying the result for use in Codex CLI.

Phase 2 adds a foreground background-daemon workflow with a global toggle hotkey. The daemon records audio, streams it to Deepgram for transcription, and delivers text back to the focused terminal. Auto-submit remains disabled.

## Phase 1 Commands

- `voice-codex-preflight`
- `voice-codex-once`
- `voice-codex-daemon`

Default transcription model:

- Engine: `deepgram-flux`
- Endpoint: `wss://api.deepgram.com/v2/listen`
- Model: `flux-general-en`
- API key environment variable: `DEEPGRAM_API_KEY`
- Audio sent to Deepgram: `linear16`, `16000` Hz, mono

See `TESTING.md` for setup and verification steps.

## Daemon Usage

```bash
voice-codex-daemon
```

Default hotkey:

```text
Ctrl+Alt+R
```

Press once to start recording and press again to stop, transcribe, and copy or insert the result. On Wayland, global keyboard listeners may be blocked by the desktop session; use `voice-codex-once` as the fallback while validating the daemon.
