# Voice Codex Project Summary

This project builds a Linux voice-to-Codex workflow. The goal is to let the user speak a prompt, transcribe it with Deepgram Flux, and insert the resulting text into the active Codex CLI terminal without manually copying and pasting.

The canonical agent instruction file is `AGENTS.md`. Use that file for detailed project rules, Phase 1 boundaries, safety defaults, and verification expectations.

## Active Phase

Branch: `phase-4`

Phase 4 should prove background service and active cursor paste support:

1. Run a preflight check.
2. Install the user systemd service.
3. Start the daemon in the background.
4. Use the hotkey while the cursor is focused in Codex CLI.
5. Transcribe with Deepgram Flux using `DEEPGRAM_API_KEY`.
6. Apply explicit deterministic corrections.
7. Paste into the focused cursor where supported, otherwise copy to clipboard.
8. Keep manual review and manual Enter.

## Deferred Until Later

- Silence detection.
- Fuzzy vocabulary matching.
- Wayland-specific paste beyond `ydotool`.
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
