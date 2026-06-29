# Voice Codex Project Summary

This project builds a Linux voice-to-Codex workflow. The goal is to let the user speak a prompt, transcribe it with Deepgram Flux, and insert the resulting text into the active Codex CLI terminal without manually copying and pasting.

The canonical agent instruction file is `AGENTS.md`. Use that file for detailed project rules, Phase 1 boundaries, safety defaults, and verification expectations.

## Active Phase

Branch: `phase-3`

Phase 3 should prove vocabulary and correction support:

1. Run a preflight check.
2. Load vocabulary and correction files.
3. Transcribe with Deepgram Flux using `DEEPGRAM_API_KEY`.
4. Apply explicit deterministic corrections.
5. Copy or insert the corrected result into the focused terminal.
6. Keep manual review and manual Enter.

## Deferred Until Later

- User-level systemd service.
- Silence detection.
- Fuzzy vocabulary matching.
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
