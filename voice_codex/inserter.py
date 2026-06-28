from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass


class InsertionError(RuntimeError):
    """Raised when text cannot be copied or inserted."""


@dataclass(frozen=True)
class InsertionResult:
    copied: bool
    clipboard_backend: str | None
    paste_attempted: bool
    pasted: bool
    insertion_mode: str
    message: str


def get_session_type() -> str:
    return os.environ.get("XDG_SESSION_TYPE", "").strip().lower() or "unknown"


def available_command(name: str) -> bool:
    return shutil.which(name) is not None


def choose_clipboard_backend(session_type: str | None = None) -> str | None:
    session = session_type or get_session_type()

    if session == "wayland" and available_command("wl-copy"):
        return "wl-copy"

    if session == "x11" and available_command("xclip"):
        return "xclip"

    if session == "x11" and available_command("xsel"):
        return "xsel"

    for backend in ("wl-copy", "xclip", "xsel"):
        if available_command(backend):
            return backend

    return None


def copy_to_clipboard(text: str, backend: str | None = None) -> str:
    selected_backend = backend or choose_clipboard_backend()
    if not selected_backend:
        raise InsertionError(
            "No supported clipboard backend found. Install 'wl-clipboard' on Wayland "
            "or 'xclip'/'xsel' on X11."
        )

    if selected_backend == "wl-copy":
        _copy_with_wl_copy(text)
        return selected_backend

    commands = {
        "xclip": ["xclip", "-selection", "clipboard"],
        "xsel": ["xsel", "--clipboard", "--input"],
    }

    command = commands.get(selected_backend)
    if command is None:
        raise InsertionError(f"Unsupported clipboard backend: {selected_backend}")

    try:
        subprocess.run(
            command,
            input=text.encode("utf-8"),
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode("utf-8", errors="replace").strip()
        detail = f": {stderr}" if stderr else ""
        raise InsertionError(f"Clipboard copy failed with {selected_backend}{detail}") from exc

    return selected_backend


def _copy_with_wl_copy(text: str) -> None:
    command = ["wl-copy", "--type", "text/plain;charset=utf-8"]

    try:
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
    except OSError as exc:
        raise InsertionError(f"Could not start wl-copy: {exc}") from exc

    assert process.stdin is not None
    assert process.stderr is not None

    try:
        process.stdin.write(text.encode("utf-8"))
        process.stdin.close()
    except OSError as exc:
        process.kill()
        raise InsertionError(f"Could not send text to wl-copy: {exc}") from exc

    try:
        return_code = process.wait(timeout=0.2)
    except subprocess.TimeoutExpired:
        # This is normal on some Wayland setups: wl-copy remains alive to own
        # and serve the clipboard. Leave it running instead of blocking the daemon.
        return

    if return_code != 0:
        stderr = process.stderr.read().decode("utf-8", errors="replace").strip()
        detail = f": {stderr}" if stderr else ""
        raise InsertionError(f"Clipboard copy failed with wl-copy{detail}")


def paste_into_active_window(
    *,
    paste_shortcut: str,
    session_type: str | None = None,
) -> bool:
    session = session_type or get_session_type()

    if session != "x11":
        return False

    if not available_command("xdotool"):
        return False

    try:
        subprocess.run(
            ["xdotool", "key", "--clearmodifiers", paste_shortcut],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError:
        return False

    return True


def insert_text(
    text: str,
    *,
    paste: bool,
    paste_shortcut: str,
    session_type: str | None = None,
) -> InsertionResult:
    session = session_type or get_session_type()
    backend = copy_to_clipboard(text)

    if not paste:
        return InsertionResult(
            copied=True,
            clipboard_backend=backend,
            paste_attempted=False,
            pasted=False,
            insertion_mode="clipboard-only",
            message=f"Copied transcription to clipboard with {backend}.",
        )

    pasted = paste_into_active_window(
        paste_shortcut=paste_shortcut,
        session_type=session,
    )

    if pasted:
        return InsertionResult(
            copied=True,
            clipboard_backend=backend,
            paste_attempted=True,
            pasted=True,
            insertion_mode="x11-paste",
            message="Copied transcription and pasted it into the active X11 window.",
        )

    return InsertionResult(
        copied=True,
        clipboard_backend=backend,
        paste_attempted=session == "x11",
        pasted=False,
        insertion_mode="clipboard-only",
        message="Copied transcription to clipboard. Direct paste was not available.",
    )
