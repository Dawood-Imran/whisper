# Voice Codex Project Summary

This project builds a Linux voice-to-Codex workflow. The goal is to let the user speak a prompt, transcribe it with Deepgram Flux, and insert the resulting text into the active Codex CLI terminal without manually copying and pasting.

The canonical agent instruction file is `AGENTS.md`. Use that file for detailed project rules, Phase 1 boundaries, safety defaults, and verification expectations.

## Active Phase

Branch: `phase-2`

Phase 2 should prove the hotkey daemon workflow:

1. Run a preflight check.
2. Run `voice-codex-daemon`.
3. Press `Ctrl+Alt+R` to start recording.
4. Press `Ctrl+Alt+R` again to stop recording.
5. Transcribe with Deepgram Flux using `DEEPGRAM_API_KEY`.
6. Copy or insert the result into the focused terminal.
7. Keep manual review and manual Enter.

## Deferred Until Later

- User-level systemd service.
- Silence detection.
- Wayland-specific polish beyond safe clipboard fallback.
- GUI.
- Auto-submit.

## End Of Phase Workflow

After each phase, run checks, commit the phase branch, merge it into `main`, push `main` to `origin`, then create and check out the next phase branch before continuing.

## Planning Artifacts

- `voice_codex_requirements_plan.md`
- `AGENTS.md`
- `TESTING.md`
- `.lavish/voice-codex-plan-review.html`
- `.lavish/phase-1-plan.html`
