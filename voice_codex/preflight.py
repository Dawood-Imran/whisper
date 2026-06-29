from __future__ import annotations

import importlib.util
import os
import platform
import shutil
import sys
from dataclasses import dataclass
from typing import Iterable

from voice_codex.config import TRANSCRIPTION_DEFAULTS, VOCABULARY_DEFAULTS
from voice_codex.hotkeys import session_warns_for_hotkeys
from voice_codex.inserter import ydotool_ready
from voice_codex.vocabulary import VocabularyError, load_corrections, load_vocabulary_terms


@dataclass(frozen=True)
class ToolCheck:
    name: str
    path: str | None

    @property
    def available(self) -> bool:
        return self.path is not None


@dataclass(frozen=True)
class PythonPackageCheck:
    import_name: str
    available: bool


@dataclass(frozen=True)
class AudioDevice:
    index: int
    name: str
    max_input_channels: int
    is_default_input: bool


@dataclass(frozen=True)
class PreflightReport:
    python_version: str
    platform: str
    session_type: str
    tools: tuple[ToolCheck, ...]
    packages: tuple[PythonPackageCheck, ...]
    input_devices: tuple[AudioDevice, ...]
    default_input_device: int | None
    api_key_env: str
    api_key_configured: bool
    vocabulary_terms_count: int
    corrections_count: int
    clipboard_backend: str | None
    insertion_mode: str
    warnings: tuple[str, ...]
    failures: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.failures


SYSTEM_TOOLS = (
    "ffmpeg",
    "xclip",
    "xsel",
    "wl-copy",
    "wl-paste",
    "xdotool",
    "ydotool",
    "ydotoold",
    "notify-send",
)

PYTHON_PACKAGES = (
    "sounddevice",
    "numpy",
    "pynput",
    "websockets",
    "dotenv",
)


def get_session_type() -> str:
    return os.environ.get("XDG_SESSION_TYPE", "").strip().lower() or "unknown"


def check_tools(names: Iterable[str] = SYSTEM_TOOLS) -> tuple[ToolCheck, ...]:
    return tuple(ToolCheck(name=name, path=shutil.which(name)) for name in names)


def check_python_packages(
    import_names: Iterable[str] = PYTHON_PACKAGES,
) -> tuple[PythonPackageCheck, ...]:
    return tuple(
        PythonPackageCheck(
            import_name=import_name,
            available=importlib.util.find_spec(import_name) is not None,
        )
        for import_name in import_names
    )


def list_input_devices() -> tuple[AudioDevice, ...]:
    if importlib.util.find_spec("sounddevice") is None:
        return ()

    try:
        import sounddevice as sd
    except Exception:
        return ()

    try:
        devices = sd.query_devices()
        default_input = _default_input_device_index(sd.default.device)
    except Exception:
        return ()

    input_devices: list[AudioDevice] = []
    for index, device in enumerate(devices):
        max_input_channels = int(device.get("max_input_channels", 0))
        if max_input_channels <= 0:
            continue

        input_devices.append(
            AudioDevice(
                index=index,
                name=str(device.get("name", f"Device {index}")),
                max_input_channels=max_input_channels,
                is_default_input=index == default_input,
            )
        )

    return tuple(input_devices)


def _default_input_device_index(default_device: object) -> int | None:
    if isinstance(default_device, (tuple, list)) and default_device:
        value = default_device[0]
    else:
        value = default_device

    if value is None:
        return None

    try:
        index = int(value)
    except (TypeError, ValueError):
        return None

    return index if index >= 0 else None


def choose_clipboard_backend(
    session_type: str,
    tools: Iterable[ToolCheck],
) -> str | None:
    available = {tool.name for tool in tools if tool.available}

    if session_type == "wayland" and "wl-copy" in available:
        return "wl-copy"

    if session_type == "x11" and "xclip" in available:
        return "xclip"

    if session_type == "x11" and "xsel" in available:
        return "xsel"

    if "wl-copy" in available:
        return "wl-copy"

    if "xclip" in available:
        return "xclip"

    if "xsel" in available:
        return "xsel"

    return None


def choose_insertion_mode(
    session_type: str,
    tools: Iterable[ToolCheck],
    clipboard_backend: str | None,
) -> str:
    available = {tool.name for tool in tools if tool.available}

    if session_type == "x11" and clipboard_backend and "xdotool" in available:
        return "x11-paste"

    if session_type == "wayland" and clipboard_backend and ydotool_ready():
        return "wayland-ydotool-type"

    if session_type == "unknown" and clipboard_backend and ydotool_ready():
        return "ydotool-type"

    if clipboard_backend:
        return "clipboard-only"

    if session_type == "wayland" and "ydotool" in available:
        return "ydotool-needs-clipboard"

    return "unavailable"


def run_preflight() -> PreflightReport:
    _load_dotenv_if_available()
    session_type = get_session_type()
    tools = check_tools()
    packages = check_python_packages()
    input_devices = list_input_devices()
    default_input = next(
        (device.index for device in input_devices if device.is_default_input),
        None,
    )
    clipboard_backend = choose_clipboard_backend(session_type, tools)
    insertion_mode = choose_insertion_mode(session_type, tools, clipboard_backend)
    api_key_env = TRANSCRIPTION_DEFAULTS.api_key_env
    api_key_configured = bool(os.environ.get(api_key_env, "").strip())
    vocabulary_terms_count = 0
    corrections_count = 0

    package_map = {package.import_name: package.available for package in packages}
    tool_map = {tool.name: tool.available for tool in tools}

    warnings: list[str] = []
    failures: list[str] = []

    if not package_map.get("sounddevice", False):
        failures.append("Python package 'sounddevice' is missing; recording cannot run.")

    if not package_map.get("numpy", False):
        failures.append("Python package 'numpy' is missing; recording cannot run.")

    if not package_map.get("websockets", False):
        failures.append(
            "Python package 'websockets' is missing; Deepgram Flux transcription cannot run."
        )

    if not package_map.get("pynput", False):
        failures.append("Python package 'pynput' is missing; the hotkey daemon cannot run.")

    if not api_key_configured:
        failures.append(
            f"Environment variable '{api_key_env}' is missing; Deepgram API transcription cannot run."
        )

    try:
        vocabulary_terms_count = len(load_vocabulary_terms(VOCABULARY_DEFAULTS.vocab_file))
        corrections_count = len(load_corrections(VOCABULARY_DEFAULTS.corrections_file))
    except VocabularyError as exc:
        failures.append(str(exc))

    hotkey_warning = session_warns_for_hotkeys(session_type)
    if hotkey_warning:
        warnings.append(hotkey_warning)

    if not input_devices and package_map.get("sounddevice", False):
        warnings.append("No input microphone devices were detected by sounddevice.")

    if not tool_map.get("ffmpeg", False):
        warnings.append(
            "System command 'ffmpeg' is missing; keep it installed for future audio conversion support."
        )

    if insertion_mode == "clipboard-only":
        warnings.append(
            "Direct terminal insertion is unavailable; Voice Codex can still copy text to the clipboard."
        )
    elif insertion_mode == "ydotool-needs-clipboard":
        warnings.append(
            "ydotool exists, but no supported clipboard tool was found; install wl-clipboard for Wayland copying."
        )
    elif insertion_mode == "unavailable":
        warnings.append(
            "No supported clipboard or insertion backend found. Install wl-clipboard on Wayland or xclip/xdotool on X11."
        )

    if session_type == "wayland" and not tool_map.get("wl-copy", False):
        warnings.append(
            "Wayland session detected, but 'wl-copy' is missing; install wl-clipboard for clipboard support."
        )

    if session_type == "wayland" and not ydotool_ready():
        warnings.append(
            "Wayland active paste needs 'ydotool' and a running 'ydotoold' socket; otherwise Voice Codex will copy only."
        )

    return PreflightReport(
        python_version=sys.version.split()[0],
        platform=platform.platform(),
        session_type=session_type,
        tools=tools,
        packages=packages,
        input_devices=input_devices,
        default_input_device=default_input,
        api_key_env=api_key_env,
        api_key_configured=api_key_configured,
        vocabulary_terms_count=vocabulary_terms_count,
        corrections_count=corrections_count,
        clipboard_backend=clipboard_backend,
        insertion_mode=insertion_mode,
        warnings=tuple(warnings),
        failures=tuple(failures),
    )


def format_report(report: PreflightReport) -> str:
    lines = [
        "Voice Codex preflight",
        "======================",
        f"Python: {report.python_version}",
        f"Platform: {report.platform}",
        f"Session: {report.session_type}",
        f"Transcription engine: {TRANSCRIPTION_DEFAULTS.engine}",
        f"Deepgram model: {TRANSCRIPTION_DEFAULTS.model}",
        f"Deepgram endpoint: {TRANSCRIPTION_DEFAULTS.endpoint}",
        f"Deepgram API key ({report.api_key_env}): "
        f"{'configured' if report.api_key_configured else 'missing'}",
        f"Vocabulary terms: {report.vocabulary_terms_count}",
        f"Correction rules: {report.corrections_count}",
        "",
        "Python packages:",
    ]

    for package in report.packages:
        status = "ok" if package.available else "missing"
        lines.append(f"  - {package.import_name}: {status}")

    lines.append("")
    lines.append("System tools:")
    for tool in report.tools:
        status = tool.path if tool.path else "missing"
        lines.append(f"  - {tool.name}: {status}")

    lines.append("")
    lines.append("Audio input devices:")
    if report.input_devices:
        for device in report.input_devices:
            default_marker = " default" if device.is_default_input else ""
            lines.append(
                "  - "
                f"{device.index}: {device.name} "
                f"({device.max_input_channels} input channels{default_marker})"
            )
    else:
        lines.append("  - none detected")

    lines.extend(
        [
            "",
            f"Clipboard backend: {report.clipboard_backend or 'unavailable'}",
            f"Insertion mode: {report.insertion_mode}",
        ]
    )

    if report.warnings:
        lines.append("")
        lines.append("Warnings:")
        for warning in report.warnings:
            lines.append(f"  - {warning}")

    if report.failures:
        lines.append("")
        lines.append("Failures:")
        for failure in report.failures:
            lines.append(f"  - {failure}")

    lines.append("")
    lines.append("Result: " + ("ready" if report.ok else "not ready"))

    return "\n".join(lines)


def _load_dotenv_if_available() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    load_dotenv()
