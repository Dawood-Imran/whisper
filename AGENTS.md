# Voice Codex Project Instructions

## Project Goal

Build a Linux voice-to-Codex workflow that lets the user speak a prompt and insert the transcribed text into the active Codex CLI terminal.

The target experience is:

1. User focuses the Codex CLI prompt in a terminal.
2. User triggers voice capture.
3. Audio is recorded locally.
4. Speech is transcribed through Deepgram Flux.
5. Project vocabulary and correction rules improve technical terms and names.
6. Final text is inserted into the Codex CLI prompt.
7. User reviews the prompt and manually presses Enter.

Auto-submit must stay disabled by default.

## Current Phase

The active branch for the first implementation slice is `phase-1`.

Phase 1 is a minimal proof of the core loop. Do not start with the background daemon, global hotkey, systemd service, Wayland polish, GUI, or silence detection.

Phase 1 should prove:

- The microphone can record audio.
- Deepgram Flux transcription works with the configured API key.
- Text can be copied or inserted into the focused terminal.
- The user can run a single command to exercise the flow.

## Phase 1 Scope

Build a Python package with these first commands:

- `voice-codex-preflight`
- `voice-codex-once`

`voice-codex-preflight` should inspect:

- Python version.
- Linux session type from `XDG_SESSION_TYPE`.
- Available microphone devices.
- Required system commands such as `ffmpeg`, `xclip`, `wl-copy`, `xdotool`, or `ydotool`.
- Whether the environment appears to support direct insertion or clipboard-only fallback.

`voice-codex-once` should:

- Record fixed-duration audio.
- Transcribe through Deepgram Flux using `/v2/listen`.
- Copy the resulting text to the clipboard.
- Attempt insertion into the active terminal when supported.
- Leave final submission to the user.

## Recommended Defaults

- Transcription engine: `deepgram-flux`
- Deepgram endpoint: `wss://api.deepgram.com/v2/listen`
- Deepgram model: `flux-general-en`
- API key env var: `DEEPGRAM_API_KEY`
- Sample rate: `16000`
- Channels: `1`
- First recording mode: fixed duration
- First insertion mode: clipboard plus X11 paste where available
- First shortcut default later: `Ctrl+Alt+R`, not `Ctrl+R`

## Implementation Guidance

Keep modules small and reusable so Phase 2 can daemonize the same core behavior.

Suggested package modules:

- `voice_codex/config.py`
- `voice_codex/recorder.py`
- `voice_codex/transcriber.py`
- `voice_codex/inserter.py`
- `voice_codex/preflight.py`
- `voice_codex/cli.py`

Avoid mixing daemon concerns into Phase 1 modules. The daemon should later orchestrate stable recorder, transcriber, vocabulary, and inserter functions.

## Safety and Privacy

- Send audio to Deepgram only for speech-to-text transcription.
- Do not hardcode, print, or log the Deepgram API key.
- Delete temporary audio files after transcription unless debugging is explicitly enabled.
- Do not log raw audio.
- Avoid logging full prompt text by default.
- Do not auto-submit prompts to Codex by default.

## Linux Integration Notes

X11 and Wayland need different insertion behavior.

On X11:

- Prefer clipboard plus terminal paste using `xdotool`.
- Default paste shortcut should be configurable because many terminals use `Ctrl+Shift+V`.

On Wayland:

- Direct insertion may require `ydotool` and `ydotoold`.
- Clipboard-only fallback is acceptable for Phase 1.

If direct insertion fails, preserve the transcription by copying it to the clipboard and clearly reporting that the user should paste manually.

## Testing and Verification

For Phase 1, prioritize practical verification:

- Run preflight and confirm environment detection.
- Run a short recording test.
- Run a Deepgram transcription test with `DEEPGRAM_API_KEY` configured.
- Confirm copied text is available on the clipboard.
- If X11 insertion is available, confirm text appears in the focused Codex CLI prompt.

Add automated tests for deterministic code where practical, especially config parsing, vocabulary correction, and insertion command selection. Do not block the first prototype on full hardware-dependent test automation.

## Business Logic Boundary

The business value is reducing friction while using Codex CLI. The user should stay in control of what is submitted. Any feature that removes review, records continuously, or silently changes spoken content should be treated as higher risk and deferred until the core flow is reliable.

## End Of Phase Workflow

At the end of every phase, before starting the next phase:

1. Run the relevant verification checks.
2. Commit the completed phase work on the phase branch.
3. Switch to `main`.
4. Merge the completed phase branch into `main`.
5. Push `main` to `origin`.
6. Create and check out the next phase branch.

Do not begin implementation for the next phase until this workflow is complete, unless the user explicitly asks to skip it.

## Current Planning Artifacts

- `voice_codex_requirements_plan.md`
- `TESTING.md`
- `.lavish/voice-codex-plan-review.html`
- `.lavish/phase-1-plan.html`
