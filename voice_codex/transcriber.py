from __future__ import annotations

import asyncio
import inspect
import json
import os
import time
import wave
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlencode

from voice_codex.config import TRANSCRIPTION_DEFAULTS


class TranscriptionError(RuntimeError):
    """Raised when Deepgram transcription fails."""


@dataclass(frozen=True)
class TranscriptionResult:
    text: str
    engine: str
    model: str
    elapsed_seconds: float
    event_count: int


@dataclass(frozen=True)
class FluxMessage:
    type: str
    transcript: str
    turn_index: int


def transcribe_audio(
    audio_path: Path,
    *,
    model_name: str,
    sample_rate: int,
    api_key_env: str,
    endpoint: str,
    chunk_ms: int,
    language_hints: tuple[str, ...] = (),
    close_timeout_seconds: float,
) -> TranscriptionResult:
    _load_dotenv_if_available()

    api_key = os.environ.get(api_key_env, "").strip()
    if not api_key:
        raise TranscriptionError(
            f"Deepgram API key is missing. Set {api_key_env}=your_key before running."
        )

    if chunk_ms <= 0:
        raise ValueError("chunk_ms must be greater than zero")

    if close_timeout_seconds <= 0:
        raise ValueError("close_timeout_seconds must be greater than zero")

    return asyncio.run(
        _transcribe_audio_async(
            audio_path=audio_path,
            api_key=api_key,
            model_name=model_name,
            sample_rate=sample_rate,
            endpoint=endpoint,
            chunk_ms=chunk_ms,
            language_hints=language_hints,
            close_timeout_seconds=close_timeout_seconds,
        )
    )


async def _transcribe_audio_async(
    *,
    audio_path: Path,
    api_key: str,
    model_name: str,
    sample_rate: int,
    endpoint: str,
    chunk_ms: int,
    language_hints: tuple[str, ...],
    close_timeout_seconds: float,
) -> TranscriptionResult:
    try:
        import websockets
    except ImportError as exc:
        raise TranscriptionError(
            "The 'websockets' package is required for Deepgram Flux transcription. "
            "Install dependencies with: python -m pip install -e ."
        ) from exc

    url = build_flux_url(
        endpoint=endpoint,
        model_name=model_name,
        sample_rate=sample_rate,
        language_hints=language_hints,
    )
    headers = {"Authorization": f"Token {api_key}"}
    connect_kwargs = _websocket_header_kwargs(websockets.connect, headers)
    started = time.monotonic()
    collector = _FluxTranscriptCollector()

    try:
        async with websockets.connect(url, **connect_kwargs) as websocket:
            receive_task = asyncio.create_task(_receive_flux_messages(websocket, collector))
            await _send_wav_as_linear16(
                websocket=websocket,
                audio_path=audio_path,
                expected_sample_rate=sample_rate,
                chunk_ms=chunk_ms,
            )
            await websocket.send(json.dumps({"type": "CloseStream"}))

            try:
                await asyncio.wait_for(receive_task, timeout=close_timeout_seconds)
            except asyncio.TimeoutError:
                receive_task.cancel()
                try:
                    await receive_task
                except asyncio.CancelledError:
                    pass
    except TranscriptionError:
        raise
    except Exception as exc:
        raise TranscriptionError(f"Deepgram Flux transcription failed: {exc}") from exc

    elapsed = time.monotonic() - started
    return TranscriptionResult(
        text=collector.text,
        engine=TRANSCRIPTION_DEFAULTS.engine,
        model=model_name,
        elapsed_seconds=elapsed,
        event_count=collector.event_count,
    )


def build_flux_url(
    *,
    endpoint: str,
    model_name: str,
    sample_rate: int,
    language_hints: tuple[str, ...] = (),
) -> str:
    if not endpoint.startswith("wss://"):
        raise ValueError("Deepgram Flux endpoint must use wss://")

    if "/v2/listen" not in endpoint:
        raise ValueError("Deepgram Flux requires the /v2/listen endpoint")

    if language_hints and model_name != "flux-general-multi":
        raise ValueError(
            "language_hint is only valid with model=flux-general-multi. "
            "Do not send language hints to flux-general-en."
        )

    params: list[tuple[str, str]] = [
        ("model", model_name),
        ("encoding", "linear16"),
        ("sample_rate", str(sample_rate)),
    ]
    params.extend(("language_hint", hint) for hint in language_hints)
    separator = "&" if "?" in endpoint else "?"
    return f"{endpoint}{separator}{urlencode(params)}"


def parse_flux_message(raw_message: str | bytes) -> FluxMessage | None:
    if isinstance(raw_message, bytes):
        return None

    try:
        payload = json.loads(raw_message)
    except json.JSONDecodeError:
        return None

    message_type = str(payload.get("type", ""))
    transcript = str(payload.get("transcript", "") or "").strip()
    turn_index = _extract_turn_index(payload)

    return FluxMessage(
        type=message_type,
        transcript=transcript,
        turn_index=turn_index,
    )


async def _receive_flux_messages(websocket: object, collector: "_FluxTranscriptCollector") -> None:
    async for raw_message in websocket:
        message = parse_flux_message(raw_message)
        if message is None:
            continue

        collector.record(message)
        if message.type == "CloseStream":
            break


async def _send_wav_as_linear16(
    *,
    websocket: object,
    audio_path: Path,
    expected_sample_rate: int,
    chunk_ms: int,
) -> None:
    frames_per_chunk = max(1, int(expected_sample_rate * chunk_ms / 1000))

    try:
        with wave.open(str(audio_path), "rb") as wav_file:
            _validate_wav_for_flux(wav_file, expected_sample_rate)

            while True:
                chunk = wav_file.readframes(frames_per_chunk)
                if not chunk:
                    break
                await websocket.send(chunk)
    except wave.Error as exc:
        raise TranscriptionError(f"Could not read WAV audio for Deepgram: {exc}") from exc


def _validate_wav_for_flux(wav_file: wave.Wave_read, expected_sample_rate: int) -> None:
    if wav_file.getcomptype() != "NONE":
        raise TranscriptionError("Deepgram Flux Phase 1 expects uncompressed PCM WAV audio.")

    if wav_file.getsampwidth() != 2:
        raise TranscriptionError("Deepgram Flux Phase 1 expects 16-bit linear PCM audio.")

    if wav_file.getnchannels() != 1:
        raise TranscriptionError("Deepgram Flux Phase 1 expects mono audio.")

    if wav_file.getframerate() != expected_sample_rate:
        raise TranscriptionError(
            "Recorded WAV sample rate "
            f"{wav_file.getframerate()} does not match requested sample_rate "
            f"{expected_sample_rate}."
        )


def _websocket_header_kwargs(connect_callable: object, headers: dict[str, str]) -> dict[str, object]:
    signature = inspect.signature(connect_callable)
    if "additional_headers" in signature.parameters:
        return {"additional_headers": headers}
    return {"extra_headers": headers}


def _extract_turn_index(payload: dict[str, object]) -> int:
    for key in ("turn_index", "turn", "turnIndex"):
        value = payload.get(key)
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
    return 0


def _load_dotenv_if_available() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    load_dotenv()


class _FluxTranscriptCollector:
    def __init__(self) -> None:
        self._turns: dict[int, str] = {}
        self.event_count = 0

    @property
    def text(self) -> str:
        return " ".join(
            transcript
            for _turn_index, transcript in sorted(self._turns.items())
            if transcript
        ).strip()

    def record(self, message: FluxMessage) -> None:
        self.event_count += 1
        if not message.transcript:
            return

        # Flux can emit multiple updates for the same turn. Keep the latest text
        # per turn so the final transcript does not duplicate partial results.
        self._turns[message.turn_index] = message.transcript
