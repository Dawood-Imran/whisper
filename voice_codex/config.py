from __future__ import annotations

from dataclasses import dataclass


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


RECORDING_DEFAULTS = RecordingDefaults()
TRANSCRIPTION_DEFAULTS = TranscriptionDefaults()
INSERTION_DEFAULTS = InsertionDefaults()
