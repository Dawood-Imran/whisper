from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


SERVICE_NAME = "voice-codexd.service"
DESKTOP_ENVIRONMENT_NAMES = (
    "DISPLAY",
    "WAYLAND_DISPLAY",
    "XDG_RUNTIME_DIR",
    "XDG_CURRENT_DESKTOP",
    "XDG_SESSION_TYPE",
    "DBUS_SESSION_BUS_ADDRESS",
    "XAUTHORITY",
    "YDOTOOL_SOCKET",
)


class ServiceError(RuntimeError):
    """Raised when service management fails."""


@dataclass(frozen=True)
class ServiceInstallResult:
    service_path: Path
    content: str


def user_systemd_dir() -> Path:
    return Path.home() / ".config" / "systemd" / "user"


def service_path() -> Path:
    return user_systemd_dir() / SERVICE_NAME


def build_service_file(
    *,
    python_executable: Path,
    working_directory: Path,
    log_level: str,
    extra_args: tuple[str, ...] = (),
) -> str:
    command = [
        str(python_executable),
        "-m",
        "voice_codex",
        "daemon",
        "--log-level",
        log_level,
        *extra_args,
    ]
    exec_start = " ".join(_systemd_quote(part) for part in command)
    path = os.environ.get("PATH", "")

    return "\n".join(
        [
            "[Unit]",
            "Description=Voice Codex background daemon",
            "After=graphical-session.target sound.target",
            "",
            "[Service]",
            "Type=simple",
            f"WorkingDirectory={working_directory}",
            "Environment=PYTHONUNBUFFERED=1",
            f'Environment="PATH={_systemd_escape_env(path)}"',
            "EnvironmentFile=-%h/.config/voice-codex/env",
            f"PassEnvironment={' '.join(DESKTOP_ENVIRONMENT_NAMES)}",
            f"ExecStart={exec_start}",
            "Restart=on-failure",
            "RestartSec=2",
            "",
            "[Install]",
            "WantedBy=default.target",
            "",
        ]
    )


def install_service(
    *,
    working_directory: Path,
    log_level: str = "info",
    extra_args: tuple[str, ...] = (),
) -> ServiceInstallResult:
    destination = service_path()
    destination.parent.mkdir(parents=True, exist_ok=True)
    content = build_service_file(
        python_executable=Path(sys.executable),
        working_directory=working_directory,
        log_level=log_level,
        extra_args=extra_args,
    )
    destination.write_text(content, encoding="utf-8")
    import_desktop_environment()
    run_systemctl("daemon-reload")
    return ServiceInstallResult(service_path=destination, content=content)


def run_systemctl(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    command = ["systemctl", "--user", *args]
    try:
        return subprocess.run(
            command,
            check=check,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError as exc:
        raise ServiceError("systemctl was not found on this system.") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        suffix = f": {detail}" if detail else ""
        raise ServiceError(f"systemctl --user {' '.join(args)} failed{suffix}") from exc


def import_desktop_environment() -> None:
    run_systemctl("import-environment", *DESKTOP_ENVIRONMENT_NAMES, check=False)


def start_service() -> None:
    run_systemctl("start", SERVICE_NAME)


def stop_service() -> None:
    run_systemctl("stop", SERVICE_NAME)


def restart_service() -> None:
    run_systemctl("restart", SERVICE_NAME)


def enable_service() -> None:
    run_systemctl("enable", SERVICE_NAME)


def disable_service() -> None:
    run_systemctl("disable", SERVICE_NAME)


def service_status() -> str:
    result = run_systemctl("status", SERVICE_NAME, "--no-pager", check=False)
    return (result.stdout or result.stderr).strip()


def service_logs(lines: int = 80) -> str:
    command = [
        "journalctl",
        "--user",
        "-u",
        SERVICE_NAME,
        "-n",
        str(lines),
        "--no-pager",
    ]
    try:
        result = subprocess.run(
            command,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError as exc:
        raise ServiceError("journalctl was not found on this system.") from exc

    return (result.stdout or result.stderr).strip()


def _systemd_quote(value: str) -> str:
    if not value:
        return '""'

    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    if any(char.isspace() for char in value):
        return f'"{escaped}"'
    return escaped


def _systemd_escape_env(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
