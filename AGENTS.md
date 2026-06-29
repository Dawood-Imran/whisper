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

The active branch for the fourth implementation slice is `phase-4`.

Phase 4 adds user-level background service management and best-effort active cursor paste. Do not add GUI, auto-submit, fuzzy matching, or silence detection yet.

Phase 4 should prove:

- The user can install `voice-codexd.service` as a `systemd --user` service.
- The user can start, stop, restart, inspect status, and view logs from CLI commands.
- The daemon keeps running in the background after service start.
- Desktop notifications show recording, transcription, copied/pasted, and error states when `notify-send` is available.
- On X11, active paste uses `xdotool` where available.
- On Wayland, active paste uses `ydotool` where available and falls back to clipboard-only otherwise.

## Phase 4 Scope

Keep the existing commands:

- `voice-codex-preflight`
- `voice-codex-once`
- `voice-codex-daemon`
- `voice-codex daemon`
- `voice-codex service install`
- `voice-codex service start`
- `voice-codex service stop`
- `voice-codex service restart`
- `voice-codex service status`
- `voice-codex service logs`

Add support for:

- `~/.config/voice-codex/vocabulary.txt`
- `~/.config/voice-codex/corrections.toml`
- `--vocab-file`
- `--corrections-file`
- `--no-vocabulary`

`voice-codex-preflight` should inspect:

- Python version.
- Linux session type from `XDG_SESSION_TYPE`.
- Available microphone devices.
- Python packages needed for recording, Deepgram, and hotkeys.
- Required system commands such as `ffmpeg`, `xclip`, `wl-copy`, `xdotool`, or `ydotool`.
- Whether the environment appears to support direct insertion or clipboard-only fallback.

`voice-codex-daemon` should:

- Listen for `F9` by default.
- Start recording on the first hotkey press.
- Stop recording on the second hotkey press.
- Transcribe through Deepgram Flux using `/v2/listen`.
- Copy the resulting text to the clipboard.
- Attempt insertion into the active terminal when supported.
- Leave final submission to the user.

Vocabulary correction should:

- Run after Deepgram transcription and before clipboard insertion.
- Apply only explicit deterministic rules.
- Avoid fuzzy matching in Phase 3.
- Treat missing files as empty configuration.

Background service support should:

- Install `~/.config/systemd/user/voice-codexd.service`.
- Use the current Python executable and project working directory at install time.
- Use `systemctl --user` for start/stop/restart/status.
- Use `journalctl --user -u voice-codexd.service` for logs.

## Recommended Defaults

- Transcription engine: `deepgram-flux`
- Deepgram endpoint: `wss://api.deepgram.com/v2/listen`
- Deepgram model: `flux-general-en`
- API key env var: `DEEPGRAM_API_KEY`
- Sample rate: `16000`
- Channels: `1`
- Daemon recording mode: manual hotkey toggle
- Maximum daemon recording duration: `45` seconds
- First insertion mode: clipboard plus X11 paste where available
- Hotkey default: `F9`, not `Ctrl+R`
- Vocabulary file: `~/.config/voice-codex/vocabulary.txt`
- Corrections file: `~/.config/voice-codex/corrections.toml`
- User service file: `~/.config/systemd/user/voice-codexd.service`
- Wayland active paste backend: `ydotool` plus `ydotoold`
- Recording indicator backend: `notify-send`

## Implementation Guidance

Keep modules small and reusable so daemon, service, and one-shot flows share the same core behavior.

Suggested package modules:

- `voice_codex/config.py`
- `voice_codex/recorder.py`
- `voice_codex/transcriber.py`
- `voice_codex/inserter.py`
- `voice_codex/hotkeys.py`
- `voice_codex/daemon.py`
- `voice_codex/vocabulary.py`
- `voice_codex/service.py`
- `voice_codex/preflight.py`
- `voice_codex/cli.py`

Keep daemon orchestration separate from the fixed-duration one-shot command. The daemon should call stable recorder, transcriber, and inserter functions rather than duplicating them.

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
- Clipboard-only fallback is acceptable when direct insertion is unavailable.

If direct insertion fails, preserve the transcription by copying it to the clipboard and clearly reporting that the user should paste manually.

## Testing and Verification

For Phase 1, prioritize practical verification:

- Run preflight and confirm environment detection.
- Run a short recording test.
- Run a Deepgram transcription test with `DEEPGRAM_API_KEY` configured.
- Confirm copied text is available on the clipboard.
- If X11 insertion is available, confirm text appears in the focused Codex CLI prompt.

For Phase 2, also verify:

- `voice-codex-daemon --help` works.
- The daemon starts and reports the configured hotkey.
- The hotkey starts/stops recording in the target desktop session.
- If global hotkeys are blocked on Wayland, the daemon reports the limitation clearly and `voice-codex-once` remains usable.

For Phase 3, also verify:

- `voice-codex-preflight` reports vocabulary and correction counts.
- Correction rules apply in `voice-codex-once`.
- Correction rules apply in `voice-codex-daemon`.
- `--no-vocabulary` disables correction behavior.

For Phase 4, also verify:

- `voice-codex service install` writes the user service file.
- `voice-codex service start` starts the background daemon.
- `voice-codex service status` shows the daemon state.
- `voice-codex service logs` shows daemon logs.
- On Wayland, installing/configuring `ydotool` enables paste into the focused cursor; without it, clipboard-only fallback remains expected.

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
