from __future__ import annotations

import wave
from pathlib import Path


class RecordingError(RuntimeError):
    """Raised when microphone recording fails."""


def record_to_wav(
    output_path: Path,
    *,
    duration_seconds: float,
    sample_rate: int,
    channels: int,
    input_device: int | str | None = None,
) -> Path:
    if duration_seconds <= 0:
        raise ValueError("duration_seconds must be greater than zero")

    if channels <= 0:
        raise ValueError("channels must be greater than zero")

    try:
        import sounddevice as sd
    except ImportError as exc:
        raise RecordingError(
            "The 'sounddevice' package is required for recording. "
            "Install dependencies with: python -m pip install -e ."
        ) from exc

    frames = int(duration_seconds * sample_rate)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        audio = sd.rec(
            frames,
            samplerate=sample_rate,
            channels=channels,
            dtype="int16",
            device=input_device,
        )
        sd.wait()
    except Exception as exc:
        raise RecordingError(f"Recording failed: {exc}") from exc

    try:
        with wave.open(str(output_path), "wb") as wav_file:
            wav_file.setnchannels(channels)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio.tobytes())
    except Exception as exc:
        raise RecordingError(f"Could not write WAV file '{output_path}': {exc}") from exc

    return output_path
