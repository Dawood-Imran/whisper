# Voice Codex

Voice Codex is a Linux command-line prototype for speaking a prompt, transcribing it with Deepgram Flux, and inserting or copying the result for use in Codex CLI.

Phase 1 intentionally avoids the daemon, global hotkey, systemd service, silence detection, GUI, and auto-submit behavior. The first goal is to prove that this machine can record audio, stream it to Deepgram for transcription, and deliver text back to the focused terminal.

## Phase 1 Commands

- `voice-codex-preflight`
- `voice-codex-once`

Default transcription model:

- Engine: `deepgram-flux`
- Endpoint: `wss://api.deepgram.com/v2/listen`
- Model: `flux-general-en`
- API key environment variable: `DEEPGRAM_API_KEY`
- Audio sent to Deepgram: `linear16`, `16000` Hz, mono

See `TESTING.md` for setup and verification steps.
