from __future__ import annotations

import logging
import signal
import tempfile
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from voice_codex.config import (
    DAEMON_DEFAULTS,
    INSERTION_DEFAULTS,
    RECORDING_DEFAULTS,
    TRANSCRIPTION_DEFAULTS,
    VOCABULARY_DEFAULTS,
)
from voice_codex.hotkeys import PynputHotkeyListener, session_warns_for_hotkeys
from voice_codex.inserter import InsertionError, insert_text
from voice_codex.notify import notify_user
from voice_codex.recorder import RecordingError, ToggleWavRecorder
from voice_codex.transcriber import TranscriptionError, transcribe_audio, warm_up_transcriber
from voice_codex.vocabulary import VocabularyConfig, VocabularyError, apply_vocabulary


LOGGER = logging.getLogger("voice_codex.daemon")


@dataclass(frozen=True)
class DaemonOptions:
    hotkey: str = DAEMON_DEFAULTS.hotkey
    max_duration_seconds: float = DAEMON_DEFAULTS.max_duration_seconds
    keep_audio: bool = DAEMON_DEFAULTS.keep_audio
    notifications_enabled: bool = DAEMON_DEFAULTS.notifications_enabled
    sample_rate: int = RECORDING_DEFAULTS.sample_rate
    channels: int = RECORDING_DEFAULTS.channels
    input_device: int | str | None = None
    engine: str = TRANSCRIPTION_DEFAULTS.engine
    model_name: str = TRANSCRIPTION_DEFAULTS.model
    device: str = TRANSCRIPTION_DEFAULTS.device
    compute_type: str = TRANSCRIPTION_DEFAULTS.compute_type
    cpu_threads: int = TRANSCRIPTION_DEFAULTS.cpu_threads
    beam_size: int = TRANSCRIPTION_DEFAULTS.beam_size
    language: str | None = TRANSCRIPTION_DEFAULTS.language
    vad_filter: bool = TRANSCRIPTION_DEFAULTS.vad_filter
    condition_on_previous_text: bool = TRANSCRIPTION_DEFAULTS.condition_on_previous_text
    endpoint: str = TRANSCRIPTION_DEFAULTS.endpoint
    api_key_env: str = TRANSCRIPTION_DEFAULTS.api_key_env
    chunk_ms: int = TRANSCRIPTION_DEFAULTS.chunk_ms
    close_timeout_seconds: float = TRANSCRIPTION_DEFAULTS.close_timeout_seconds
    language_hints: tuple[str, ...] = ()
    paste: bool = INSERTION_DEFAULTS.paste
    paste_shortcut: str = INSERTION_DEFAULTS.paste_shortcut
    audio_dir: Path | None = None
    vocabulary_enabled: bool = VOCABULARY_DEFAULTS.enabled
    vocab_file: Path = VOCABULARY_DEFAULTS.vocab_file
    corrections_file: Path = VOCABULARY_DEFAULTS.corrections_file


class VoiceCodexDaemon:
    def __init__(self, options: DaemonOptions) -> None:
        self.options = options
        self._lock = threading.Lock()
        self._state = "idle"
        self._recorder: ToggleWavRecorder | None = None
        self._stop_event = threading.Event()
        self._max_duration_timer: threading.Timer | None = None
        self._temp_dir: tempfile.TemporaryDirectory[str] | None = None

    @property
    def state(self) -> str:
        with self._lock:
            return self._state

    def run(self) -> int:
        _configure_signal_handlers(self.stop)
        warning = session_warns_for_hotkeys()
        if warning:
            LOGGER.warning(warning)

        LOGGER.info("Voice Codex daemon started. Hotkey: %s", self.options.hotkey)
        LOGGER.info("Press the hotkey once to start recording, again to stop.")
        try:
            self._warm_up_transcription()
        except (TranscriptionError, ValueError) as exc:
            LOGGER.error("Could not initialize transcription engine: %s", exc)
            self._notify("Voice Codex error", str(exc), urgency="critical", timeout_ms=6000)
            return 1

        self._notify("Voice Codex ready", f"Press {self.options.hotkey} to start recording.")
        listener = PynputHotkeyListener(self.options.hotkey, self.toggle_recording)

        try:
            listener.run()
        finally:
            self.stop()

        return 0

    def stop(self) -> None:
        self._stop_event.set()
        with self._lock:
            recorder = self._recorder
            self._recorder = None
            self._state = "stopped"
            self._cancel_timer_locked()

        if recorder is not None:
            recorder.abort()

    def toggle_recording(self) -> None:
        with self._lock:
            state = self._state

        if state == "idle":
            try:
                self.start_recording()
            except RecordingError as exc:
                LOGGER.error("Could not start recording: %s", exc)
                self._notify("Voice Codex error", str(exc), urgency="critical", timeout_ms=5000)
                self._return_to_idle()
            return

        if state == "recording":
            self.stop_recording_and_process()
            return

        LOGGER.info("Ignoring hotkey while daemon state is '%s'.", state)

    def start_recording(self) -> None:
        with self._lock:
            if self._state != "idle":
                LOGGER.info("Cannot start recording while daemon state is '%s'.", self._state)
                return

            audio_path = self._next_audio_path()
            recorder = ToggleWavRecorder(
                audio_path,
                sample_rate=self.options.sample_rate,
                channels=self.options.channels,
                input_device=self.options.input_device,
            )

            try:
                recorder.start()
            except RecordingError:
                self._cleanup_temp_dir()
                raise
            except Exception as exc:
                self._cleanup_temp_dir()
                raise RecordingError(f"Could not start daemon recording: {exc}") from exc

            self._recorder = recorder
            self._state = "recording"
            self._schedule_max_duration_locked()

        LOGGER.info("Recording started.")
        self._notify("Recording started", f"Press {self.options.hotkey} again to stop.", urgency="normal")

    def stop_recording_and_process(self) -> None:
        with self._lock:
            if self._state != "recording" or self._recorder is None:
                LOGGER.info("No active recording to stop.")
                return

            recorder = self._recorder
            self._recorder = None
            self._state = "processing"
            self._cancel_timer_locked()

        try:
            result = recorder.stop()
        except RecordingError as exc:
            LOGGER.error("Recording failed: %s", exc)
            self._return_to_idle()
            return

        LOGGER.info(
            "Recording stopped after %.2fs. Audio: %s",
            result.duration_seconds,
            result.audio_path,
        )
        self._notify("Recording stopped", f"Transcribing with {self.options.engine}.")
        if result.status_messages:
            LOGGER.warning("Recording status messages: %s", "; ".join(result.status_messages))

        worker = threading.Thread(
            target=self._process_recording,
            args=(result.audio_path,),
            name="voice-codex-process-recording",
            daemon=True,
        )
        worker.start()

    def _process_recording(self, audio_path: Path) -> None:
        try:
            LOGGER.info("Processing recording with %s.", self.options.engine)
            self._notify("Transcribing", self._transcription_notification_body())
            transcription = transcribe_audio(
                audio_path,
                engine=self.options.engine,
                model_name=self.options.model_name,
                sample_rate=self.options.sample_rate,
                api_key_env=self.options.api_key_env,
                endpoint=self.options.endpoint,
                chunk_ms=self.options.chunk_ms,
                language_hints=self.options.language_hints,
                close_timeout_seconds=self.options.close_timeout_seconds,
                device=self.options.device,
                compute_type=self.options.compute_type,
                cpu_threads=self.options.cpu_threads,
                beam_size=self.options.beam_size,
                language=self.options.language,
                vad_filter=self.options.vad_filter,
                condition_on_previous_text=self.options.condition_on_previous_text,
            )

            if not transcription.text:
                LOGGER.warning("%s returned no transcript text.", transcription.engine)
                self._notify("No transcript", f"{transcription.engine} returned no text.", urgency="normal")
                return

            vocabulary = apply_vocabulary(
                transcription.text,
                VocabularyConfig(
                    enabled=self.options.vocabulary_enabled,
                    vocab_file=self.options.vocab_file,
                    corrections_file=self.options.corrections_file,
                ),
            )
            if vocabulary.correction_count:
                LOGGER.info(
                    "Applied %d vocabulary corrections before copying.",
                    vocabulary.correction_count,
                )

            LOGGER.info(
                "Transcribed %d chars from %d %s in %.2fs. Copying result.",
                len(vocabulary.text),
                transcription.event_count,
                self._transcription_count_label(transcription.engine),
                transcription.elapsed_seconds,
            )
            insertion = insert_text(
                vocabulary.text,
                paste=self.options.paste,
                paste_shortcut=self.options.paste_shortcut,
            )
            LOGGER.info(insertion.message)
            if insertion.pasted:
                self._notify("Transcript inserted", "Review the prompt before pressing Enter.")
            else:
                self._notify("Transcript copied", "Paste into Codex, then press Enter.")
            if insertion.insertion_mode == "clipboard-only":
                LOGGER.info("Paste manually into Codex CLI, then press Enter when ready.")
            else:
                LOGGER.info("Review the inserted Codex prompt, then press Enter when ready.")
        except (TranscriptionError, InsertionError, VocabularyError, ValueError) as exc:
            LOGGER.error("Could not process recording: %s", exc)
            self._notify("Voice Codex error", str(exc), urgency="critical", timeout_ms=6000)
        except Exception:
            LOGGER.exception("Unexpected daemon processing error.")
            self._notify("Voice Codex error", "Unexpected processing error.", urgency="critical", timeout_ms=6000)
        finally:
            if not self.options.keep_audio:
                try:
                    audio_path.unlink(missing_ok=True)
                except OSError as exc:
                    LOGGER.warning("Could not delete temporary audio file %s: %s", audio_path, exc)
            self._return_to_idle()

    def _return_to_idle(self) -> None:
        with self._lock:
            if self._state != "stopped":
                self._state = "idle"
            self._cleanup_temp_dir()

        LOGGER.info("Daemon ready.")

    def _warm_up_transcription(self) -> None:
        if self.options.engine != "faster-whisper":
            return

        LOGGER.info(
            "Loading faster-whisper model %s on %s with compute_type=%s.",
            self.options.model_name,
            self.options.device,
            self.options.compute_type,
        )
        self._notify("Loading speech model", f"{self.options.model_name} on {self.options.device}.")
        warm_up_transcriber(
            engine=self.options.engine,
            model_name=self.options.model_name,
            device=self.options.device,
            compute_type=self.options.compute_type,
            cpu_threads=self.options.cpu_threads,
        )
        LOGGER.info("faster-whisper model loaded.")

    def _transcription_notification_body(self) -> str:
        if self.options.engine == "faster-whisper":
            return f"Running {self.options.model_name} locally."

        return "Sending audio to Deepgram."

    @staticmethod
    def _transcription_count_label(engine: str) -> str:
        return "segments" if engine == "faster-whisper" else "Deepgram events"

    def _notify(
        self,
        summary: str,
        body: str = "",
        *,
        urgency: str = "normal",
        timeout_ms: int = 2500,
    ) -> None:
        if not self.options.notifications_enabled:
            return

        notify_user(summary, body, urgency=urgency, timeout_ms=timeout_ms)

    def _next_audio_path(self) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        if self.options.keep_audio:
            audio_dir = self.options.audio_dir or Path.cwd()
            audio_dir.mkdir(parents=True, exist_ok=True)
            return audio_dir / f"voice-codex-daemon-{timestamp}.wav"

        self._temp_dir = tempfile.TemporaryDirectory(prefix="voice-codex-daemon-")
        return Path(self._temp_dir.name) / "voice-codex-daemon.wav"

    def _schedule_max_duration_locked(self) -> None:
        self._cancel_timer_locked()
        if self.options.max_duration_seconds <= 0:
            return

        self._max_duration_timer = threading.Timer(
            self.options.max_duration_seconds,
            self._max_duration_reached,
        )
        self._max_duration_timer.daemon = True
        self._max_duration_timer.start()

    def _cancel_timer_locked(self) -> None:
        if self._max_duration_timer is not None:
            self._max_duration_timer.cancel()
            self._max_duration_timer = None

    def _max_duration_reached(self) -> None:
        LOGGER.info(
            "Maximum recording duration %.1fs reached; stopping recording.",
            self.options.max_duration_seconds,
        )
        self.stop_recording_and_process()

    def _cleanup_temp_dir(self) -> None:
        if self._temp_dir is None:
            return

        self._temp_dir.cleanup()
        self._temp_dir = None


def run_daemon(options: DaemonOptions) -> int:
    daemon = VoiceCodexDaemon(options)
    return daemon.run()


def _configure_signal_handlers(stop_callback: object) -> None:
    def handle_signal(_signum: int, _frame: object) -> None:
        LOGGER.info("Stopping Voice Codex daemon.")
        stop_callback()
        raise SystemExit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
