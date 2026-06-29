from __future__ import annotations

import shutil
import subprocess


def notify_user(
    summary: str,
    body: str = "",
    *,
    urgency: str = "normal",
    timeout_ms: int = 2500,
) -> bool:
    if shutil.which("notify-send") is None:
        return False

    command = [
        "notify-send",
        "--app-name",
        "Voice Codex",
        "--icon",
        "audio-input-microphone",
        "--urgency",
        urgency,
        "--expire-time",
        str(timeout_ms),
        summary,
    ]
    if body:
        command.append(body)

    try:
        subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError:
        return False

    return True
