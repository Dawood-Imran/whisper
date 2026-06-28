from __future__ import annotations

import threading
import time
import wave
from dataclasses import dataclass
from pathlib import Path


class RecordingError(RuntimeError):
    """Raised when microphone recording fails."""


class RecordingStateError(RecordingError):
    """Raised when a toggle recorder is used in the wrong state."""


@dataclass(frozen=True)
class RecordingResult:
    audio_path: Path
    duration_seconds: float
    bytes_written: int
    status_messages: tuple[str, ...]


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


class ToggleWavRecorder:
    def __init__(
        self,
        output_path: Path,
        *,
        sample_rate: int,
        channels: int,
        input_device: int | str | None = None,
    ) -> None:
        if channels <= 0:
            raise ValueError("channels must be greater than zero")

        if sample_rate <= 0:
            raise ValueError("sample_rate must be greater than zero")

        self.output_path = output_path
        self.sample_rate = sample_rate
        self.channels = channels
        self.input_device = input_device
        self._chunks: list[bytes] = []
        self._status_messages: list[str] = []
        self._lock = threading.Lock()
        self._stream: object | None = None
        self._started_at: float | None = None

    @property
    def is_recording(self) -> bool:
        return self._stream is not None

    @property
    def elapsed_seconds(self) -> float:
        if self._started_at is None:
            return 0.0
        return time.monotonic() - self._started_at

    def start(self) -> None:
        if self._stream is not None:
            raise RecordingStateError("Recording is already active.")

        try:
            import sounddevice as sd
        except ImportError as exc:
            raise RecordingError(
                "The 'sounddevice' package is required for recording. "
                "Install dependencies with: python -m pip install -e ."
            ) from exc

        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self._chunks.clear()
        self._status_messages.clear()
        self._started_at = time.monotonic()

        def callback(indata: object, _frames: int, _time_info: object, status: object) -> None:
            if status:
                with self._lock:
                    self._status_messages.append(str(status))

            with self._lock:
                self._chunks.append(indata.copy().tobytes())

        try:
            stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="int16",
                device=self.input_device,
                callback=callback,
            )
            stream.start()
        except Exception as exc:
            self._started_at = None
            self._stream = None
            raise RecordingError(f"Could not start recording stream: {exc}") from exc

        self._stream = stream

    def stop(self) -> RecordingResult:
        stream = self._stream
        if stream is None:
            raise RecordingStateError("Recording is not active.")

        duration = self.elapsed_seconds

        try:
            stream.stop()
            stream.close()
        except Exception as exc:
            raise RecordingError(f"Could not stop recording stream: {exc}") from exc
        finally:
            self._stream = None
            self._started_at = None

        with self._lock:
            chunks = tuple(self._chunks)
            status_messages = tuple(self._status_messages)

        bytes_written = sum(len(chunk) for chunk in chunks)
        try:
            with wave.open(str(self.output_path), "wb") as wav_file:
                wav_file.setnchannels(self.channels)
                wav_file.setsampwidth(2)
                wav_file.setframerate(self.sample_rate)
                for chunk in chunks:
                    wav_file.writeframes(chunk)
        except Exception as exc:
            raise RecordingError(
                f"Could not write WAV file '{self.output_path}': {exc}"
            ) from exc

        return RecordingResult(
            audio_path=self.output_path,
            duration_seconds=duration,
            bytes_written=bytes_written,
            status_messages=status_messages,
        )

    def abort(self) -> None:
        stream = self._stream
        self._stream = None
        self._started_at = None
        self._chunks.clear()
        self._status_messages.clear()

        if stream is None:
            return

        try:
            stream.stop()
            stream.close()
        except Exception:
            return
