from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RecordingDefaults:
    sample_rate: int = 16_000
    channels: int = 1
    duration_seconds: float = 8.0


@dataclass(frozen=True)
class TranscriptionDefaults:
    engine: str = "deepgram-flux"
    model: str = "flux-general-en"
    endpoint: str = "wss://api.deepgram.com/v2/listen"
    api_key_env: str = "DEEPGRAM_API_KEY"
    chunk_ms: int = 80
    close_timeout_seconds: float = 10.0


@dataclass(frozen=True)
class InsertionDefaults:
    paste_shortcut: str = "ctrl+shift+v"
    paste: bool = True


@dataclass(frozen=True)
class DaemonDefaults:
    hotkey: str = "<ctrl>+<alt>+r"
    max_duration_seconds: float = 45.0
    keep_audio: bool = False


@dataclass(frozen=True)
class VocabularyDefaults:
    enabled: bool = True
    vocab_file: Path = Path("~/.config/voice-codex/vocabulary.txt")
    corrections_file: Path = Path("~/.config/voice-codex/corrections.toml")


RECORDING_DEFAULTS = RecordingDefaults()
TRANSCRIPTION_DEFAULTS = TranscriptionDefaults()
INSERTION_DEFAULTS = InsertionDefaults()
DAEMON_DEFAULTS = DaemonDefaults()
VOCABULARY_DEFAULTS = VocabularyDefaults()
