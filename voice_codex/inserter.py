from __future__ import annotations

import logging
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


LOGGER = logging.getLogger(__name__)


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


@dataclass(frozen=True)
class YdotoolStatus:
    ready: bool
    reason: str


def get_session_type() -> str:
    return os.environ.get("XDG_SESSION_TYPE", "").strip().lower() or "unknown"


def available_command(name: str) -> bool:
    return command_path(name) is not None


def command_path(name: str) -> str | None:
    resolved = shutil.which(name)
    if resolved:
        return resolved

    for directory in ("/usr/bin", "/usr/local/bin", "/bin"):
        candidate = Path(directory) / name
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)

    return None


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
        "xclip": [command_path("xclip") or "xclip", "-selection", "clipboard"],
        "xsel": [command_path("xsel") or "xsel", "--clipboard", "--input"],
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
    command = [command_path("wl-copy") or "wl-copy", "--type", "text/plain;charset=utf-8"]

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
    text: str,
    paste_shortcut: str,
    session_type: str | None = None,
) -> bool:
    session = session_type or get_session_type()

    if session == "wayland":
        return type_with_ydotool(text)

    if session != "x11":
        status = ydotool_status()
        if status.ready:
            LOGGER.info(
                "Session type is '%s'; trying ydotool direct typing because %s.",
                session,
                status.reason,
            )
            return type_with_ydotool(text)

        LOGGER.info(
            "Direct paste unavailable: session type is '%s' and %s.",
            session,
            status.reason,
        )
        return False

    xdotool = command_path("xdotool")
    if not xdotool:
        LOGGER.info("Direct paste unavailable: xdotool is not installed.")
        return False

    try:
        subprocess.run(
            [xdotool, "key", "--clearmodifiers", paste_shortcut],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode("utf-8", errors="replace").strip()
        detail = f": {stderr}" if stderr else ""
        LOGGER.warning("xdotool paste command failed%s", detail)
        return False

    return True


def type_with_ydotool(text: str) -> bool:
    ydotool = command_path("ydotool")
    if not ydotool:
        LOGGER.info("Direct typing unavailable: ydotool is not installed.")
        return False

    status = ydotool_status()
    if not status.ready:
        LOGGER.info("Direct typing unavailable: %s.", status.reason)
        return False

    type_text = text.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    if not type_text:
        LOGGER.info("Direct typing unavailable: transcript is empty.")
        return False

    command = [
        ydotool,
        "type",
        "--delay",
        "150",
        "--key-delay",
        "8",
        "--file",
        "-",
    ]

    try:
        subprocess.run(
            command,
            input=type_text.encode("utf-8"),
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=max(5, min(30, len(type_text) * 0.08)),
        )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode("utf-8", errors="replace").strip()
        detail = f": {stderr}" if stderr else ""
        LOGGER.warning("ydotool direct typing failed%s", detail)
        return False
    except subprocess.TimeoutExpired:
        LOGGER.warning("ydotool direct typing timed out.")
        return False

    return True


def paste_with_ydotool() -> bool:
    ydotool = command_path("ydotool")
    if not ydotool:
        LOGGER.info("Direct paste unavailable: ydotool is not installed.")
        return False

    status = ydotool_status()
    if not status.ready:
        LOGGER.info("Direct paste unavailable: %s.", status.reason)
        return False

    # Linux input key codes: leftctrl=29, leftshift=42, v=47.
    command = [ydotool, "key", "29:1", "42:1", "47:1", "47:0", "42:0", "29:0"]

    try:
        subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=3,
        )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode("utf-8", errors="replace").strip()
        detail = f": {stderr}" if stderr else ""
        LOGGER.warning("ydotool paste command failed%s", detail)
        return False
    except subprocess.TimeoutExpired:
        LOGGER.warning("ydotool paste command timed out.")
        return False

    return True


def ydotool_ready() -> bool:
    return ydotool_status().ready


def ydotool_status() -> YdotoolStatus:
    if command_path("ydotool") is None:
        return YdotoolStatus(False, "ydotool is not installed")

    socket_paths = []
    configured_socket = os.environ.get("YDOTOOL_SOCKET")
    if configured_socket:
        socket_paths.append(Path(configured_socket))

    socket_paths.extend(
        [
            Path("/tmp/.ydotool_socket"),
            Path(f"/run/user/{os.getuid()}/.ydotool_socket"),
        ]
    )

    problems: list[str] = []
    for path in socket_paths:
        if path.is_socket() and os.access(path, os.R_OK | os.W_OK):
            return YdotoolStatus(True, f"ydotoold socket is ready at {path}")

        if path.is_socket():
            problems.append(f"{path} is not readable/writable by uid {os.getuid()}")
        elif path.exists():
            problems.append(f"{path} exists but is not a socket")
        else:
            problems.append(f"{path} does not exist")

    return YdotoolStatus(False, "; ".join(problems))


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
        text=text,
        paste_shortcut=paste_shortcut,
        session_type=session,
    )

    if pasted:
        if session == "x11":
            mode = "x11-paste"
        elif session == "wayland":
            mode = "wayland-ydotool-type"
        else:
            mode = "ydotool-type"

        return InsertionResult(
            copied=True,
            clipboard_backend=backend,
            paste_attempted=True,
            pasted=True,
            insertion_mode=mode,
            message="Copied transcription and inserted it into the active window.",
        )

    return InsertionResult(
        copied=True,
        clipboard_backend=backend,
        paste_attempted=session in {"x11", "wayland"},
        pasted=False,
        insertion_mode="clipboard-only",
        message="Copied transcription to clipboard. Direct paste was not available.",
    )
