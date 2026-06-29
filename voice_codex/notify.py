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
        subprocess.run(
            command,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=2,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False

    return True
