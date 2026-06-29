from __future__ import annotations

import os
from collections.abc import Callable


class HotkeyError(RuntimeError):
    """Raised when global hotkey listening cannot start."""


MODIFIER_ALIASES = {
    "ctrl": "<ctrl>",
    "control": "<ctrl>",
    "alt": "<alt>",
    "shift": "<shift>",
    "cmd": "<cmd>",
    "command": "<cmd>",
    "super": "<cmd>",
    "win": "<cmd>",
}

KEY_ALIASES = {
    "space": "<space>",
    "enter": "<enter>",
    "return": "<enter>",
    "esc": "<esc>",
    "escape": "<esc>",
    "tab": "<tab>",
}


def normalize_hotkey(hotkey: str) -> str:
    parts = [part.strip().lower() for part in hotkey.split("+") if part.strip()]
    if not parts:
        raise ValueError("Hotkey cannot be empty.")

    normalized: list[str] = []
    for part in parts:
        if part.startswith("<") and part.endswith(">"):
            normalized.append(part)
        elif part in MODIFIER_ALIASES:
            normalized.append(MODIFIER_ALIASES[part])
        elif part in KEY_ALIASES:
            normalized.append(KEY_ALIASES[part])
        else:
            normalized.append(part)

    return "+".join(normalized)


def session_warns_for_hotkeys(session_type: str | None = None) -> str | None:
    session = (session_type or os.environ.get("XDG_SESSION_TYPE", "")).strip().lower()
    if session == "wayland":
        return (
            "Wayland sessions may block global keyboard listeners. If the daemon "
            "does not receive hotkeys, use voice-codex-once as the fallback or "
            "switch to an X11 session for daemon testing."
        )
    return None


class PynputHotkeyListener:
    def __init__(self, hotkey: str, on_activate: Callable[[], None]) -> None:
        self.hotkey = normalize_hotkey(hotkey)
        self.on_activate = on_activate

    def run(self) -> None:
        try:
            from pynput import keyboard
        except ImportError as exc:
            raise HotkeyError(
                "The 'pynput' package is required for global hotkeys. "
                "Install dependencies with: python -m pip install -e ."
            ) from exc

        try:
            hotkey = keyboard.HotKey(
                keyboard.HotKey.parse(self.hotkey),
                self.on_activate,
            )
        except Exception as exc:
            raise HotkeyError(f"Invalid hotkey '{self.hotkey}': {exc}") from exc

        listener = keyboard.Listener(
            on_press=lambda key: hotkey.press(listener.canonical(key)),
            on_release=lambda key: hotkey.release(listener.canonical(key)),
        )

        try:
            listener.start()
            listener.join()
        except Exception as exc:
            raise HotkeyError(f"Global hotkey listener stopped unexpectedly: {exc}") from exc
