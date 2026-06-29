from __future__ import annotations

import argparse
import logging
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from voice_codex.config import (
    DAEMON_DEFAULTS,
    INSERTION_DEFAULTS,
    RECORDING_DEFAULTS,
    TRANSCRIPTION_DEFAULTS,
    VOCABULARY_DEFAULTS,
)
from voice_codex.daemon import DaemonOptions, run_daemon
from voice_codex.inserter import InsertionError, insert_text
from voice_codex.preflight import format_report, run_preflight
from voice_codex.recorder import RecordingError, record_to_wav
from voice_codex.service import (
    ServiceError,
    disable_service,
    enable_service,
    install_service,
    restart_service,
    service_logs,
    service_status,
    start_service,
    stop_service,
)
from voice_codex.transcriber import TranscriptionError, transcribe_audio
from voice_codex.vocabulary import VocabularyConfig, VocabularyError, apply_vocabulary


def preflight_main(argv: list[str] | None = None) -> int:
    _parser = argparse.ArgumentParser(
        prog="voice-codex-preflight",
        description="Check whether this machine is ready for Voice Codex Phase 1.",
    )
    _parser.parse_args(argv)

    report = run_preflight()
    print(format_report(report))
    return 0 if report.ok else 1


def once_main(argv: list[str] | None = None) -> int:
    parser = build_once_parser("voice-codex-once")
    args = parser.parse_args(argv)
    return run_once(args)


def daemon_main(argv: list[str] | None = None) -> int:
    parser = build_daemon_parser("voice-codex-daemon")
    args = parser.parse_args(argv)
    _configure_logging(args.log_level)
    return run_daemon(_daemon_options_from_args(args))


def service_main(argv: list[str] | None = None) -> int:
    parser = build_service_parser("voice-codex-service")
    args = parser.parse_args(argv)
    return run_service_command(args)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="voice-codex",
        description="Voice Codex command-line tools.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser(
        "preflight",
        help="Check whether this machine is ready for Voice Codex.",
    )

    once_parser = build_once_parser("voice-codex once", add_help=False)
    subparsers.add_parser(
        "once",
        parents=[once_parser],
        add_help=True,
        help="Record, transcribe, and copy or insert one spoken prompt.",
    )

    daemon_parser = build_daemon_parser("voice-codex daemon", add_help=False)
    subparsers.add_parser(
        "daemon",
        parents=[daemon_parser],
        add_help=True,
        help="Run the background hotkey daemon.",
    )

    service_parser = build_service_parser("voice-codex service", add_help=False)
    subparsers.add_parser(
        "service",
        parents=[service_parser],
        add_help=True,
        help="Install and control the user background service.",
    )

    args = parser.parse_args(argv)

    if args.command == "preflight":
        return preflight_main([])

    if args.command == "once":
        return run_once(args)

    if args.command == "daemon":
        _configure_logging(args.log_level)
        return run_daemon(_daemon_options_from_args(args))

    if args.command == "service":
        return run_service_command(args)

    parser.error(f"Unknown command: {args.command}")
    return 2


def build_once_parser(prog: str, *, add_help: bool = True) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=prog,
        description="Record, transcribe, and copy or insert one spoken prompt.",
        add_help=add_help,
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=RECORDING_DEFAULTS.duration_seconds,
        help=f"Recording duration in seconds. Default: {RECORDING_DEFAULTS.duration_seconds}",
    )
    parser.add_argument(
        "--sample-rate",
        type=int,
        default=RECORDING_DEFAULTS.sample_rate,
        help=f"Recording sample rate. Default: {RECORDING_DEFAULTS.sample_rate}",
    )
    parser.add_argument(
        "--channels",
        type=int,
        default=RECORDING_DEFAULTS.channels,
        help=f"Number of input channels. Default: {RECORDING_DEFAULTS.channels}",
    )
    parser.add_argument(
        "--input-device",
        help="Optional sounddevice input device index or name.",
    )
    parser.add_argument(
        "--audio-output",
        type=Path,
        help="Optional WAV path to keep the recorded audio.",
    )
    parser.add_argument(
        "--keep-audio",
        action="store_true",
        help="Keep the temporary WAV file and print its path.",
    )
    parser.add_argument(
        "--engine",
        choices=("faster-whisper", "deepgram-flux"),
        default=TRANSCRIPTION_DEFAULTS.engine,
        help=f"Transcription engine. Default: {TRANSCRIPTION_DEFAULTS.engine}",
    )
    parser.add_argument(
        "--model",
        default=TRANSCRIPTION_DEFAULTS.model,
        help=f"Transcription model name. Default: {TRANSCRIPTION_DEFAULTS.model}",
    )
    parser.add_argument(
        "--device",
        default=TRANSCRIPTION_DEFAULTS.device,
        help=f"faster-whisper device. Default: {TRANSCRIPTION_DEFAULTS.device}",
    )
    parser.add_argument(
        "--compute-type",
        default=TRANSCRIPTION_DEFAULTS.compute_type,
        help=f"faster-whisper compute type. Default: {TRANSCRIPTION_DEFAULTS.compute_type}",
    )
    parser.add_argument(
        "--cpu-threads",
        type=int,
        default=TRANSCRIPTION_DEFAULTS.cpu_threads,
        help=(
            "CPU threads for faster-whisper. "
            f"Default: {TRANSCRIPTION_DEFAULTS.cpu_threads} (all cores)"
        ),
    )
    parser.add_argument(
        "--beam-size",
        type=int,
        default=TRANSCRIPTION_DEFAULTS.beam_size,
        help=f"Beam size for faster-whisper. Default: {TRANSCRIPTION_DEFAULTS.beam_size}",
    )
    parser.add_argument(
        "--language",
        default=TRANSCRIPTION_DEFAULTS.language,
        help=f"Language for faster-whisper. Default: {TRANSCRIPTION_DEFAULTS.language}",
    )
    parser.add_argument(
        "--no-vad-filter",
        action="store_false",
        dest="vad_filter",
        default=TRANSCRIPTION_DEFAULTS.vad_filter,
        help="Disable faster-whisper VAD silence filtering.",
    )
    parser.add_argument(
        "--condition-on-previous-text",
        action="store_true",
        default=TRANSCRIPTION_DEFAULTS.condition_on_previous_text,
        help="Allow faster-whisper to condition each segment on previous text.",
    )
    parser.add_argument(
        "--endpoint",
        default=TRANSCRIPTION_DEFAULTS.endpoint,
        help=f"Deepgram Flux WebSocket endpoint. Default: {TRANSCRIPTION_DEFAULTS.endpoint}",
    )
    parser.add_argument(
        "--api-key-env",
        default=TRANSCRIPTION_DEFAULTS.api_key_env,
        help=f"Environment variable containing the Deepgram API key. Default: {TRANSCRIPTION_DEFAULTS.api_key_env}",
    )
    parser.add_argument(
        "--chunk-ms",
        type=int,
        default=TRANSCRIPTION_DEFAULTS.chunk_ms,
        help=f"Audio chunk size sent to Flux in milliseconds. Default: {TRANSCRIPTION_DEFAULTS.chunk_ms}",
    )
    parser.add_argument(
        "--close-timeout",
        type=float,
        default=TRANSCRIPTION_DEFAULTS.close_timeout_seconds,
        help=(
            "Seconds to wait for final Deepgram messages after sending CloseStream. "
            f"Default: {TRANSCRIPTION_DEFAULTS.close_timeout_seconds}"
        ),
    )
    parser.add_argument(
        "--language-hint",
        action="append",
        default=[],
        help=(
            "Optional language hint for model=flux-general-multi. "
            "May be passed multiple times. Do not use with flux-general-en."
        ),
    )
    parser.add_argument(
        "--no-paste",
        action="store_true",
        help="Only copy to clipboard; do not attempt active-window paste.",
    )
    parser.add_argument(
        "--paste-shortcut",
        default=INSERTION_DEFAULTS.paste_shortcut,
        help=f"X11 paste shortcut for xdotool. Default: {INSERTION_DEFAULTS.paste_shortcut}",
    )
    parser.add_argument(
        "--no-echo",
        action="store_true",
        help="Do not print the transcript to stdout.",
    )
    add_vocabulary_arguments(parser)
    return parser


def build_daemon_parser(prog: str, *, add_help: bool = True) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=prog,
        description="Run the Voice Codex background hotkey daemon.",
        add_help=add_help,
    )
    parser.add_argument(
        "--hotkey",
        default=DAEMON_DEFAULTS.hotkey,
        help=f"Global toggle hotkey. Default: {DAEMON_DEFAULTS.hotkey}",
    )
    parser.add_argument(
        "--max-duration",
        type=float,
        default=DAEMON_DEFAULTS.max_duration_seconds,
        help=(
            "Maximum recording duration before auto-stop. "
            f"Default: {DAEMON_DEFAULTS.max_duration_seconds}"
        ),
    )
    parser.add_argument(
        "--sample-rate",
        type=int,
        default=RECORDING_DEFAULTS.sample_rate,
        help=f"Recording sample rate. Default: {RECORDING_DEFAULTS.sample_rate}",
    )
    parser.add_argument(
        "--channels",
        type=int,
        default=RECORDING_DEFAULTS.channels,
        help=f"Number of input channels. Default: {RECORDING_DEFAULTS.channels}",
    )
    parser.add_argument(
        "--input-device",
        help="Optional sounddevice input device index or name.",
    )
    parser.add_argument(
        "--keep-audio",
        action="store_true",
        help="Keep daemon WAV files for debugging.",
    )
    parser.add_argument(
        "--audio-dir",
        type=Path,
        help="Directory for kept daemon WAV files. Defaults to the current directory.",
    )
    parser.add_argument(
        "--engine",
        choices=("faster-whisper", "deepgram-flux"),
        default=TRANSCRIPTION_DEFAULTS.engine,
        help=f"Transcription engine. Default: {TRANSCRIPTION_DEFAULTS.engine}",
    )
    parser.add_argument(
        "--model",
        default=TRANSCRIPTION_DEFAULTS.model,
        help=f"Transcription model name. Default: {TRANSCRIPTION_DEFAULTS.model}",
    )
    parser.add_argument(
        "--device",
        default=TRANSCRIPTION_DEFAULTS.device,
        help=f"faster-whisper device. Default: {TRANSCRIPTION_DEFAULTS.device}",
    )
    parser.add_argument(
        "--compute-type",
        default=TRANSCRIPTION_DEFAULTS.compute_type,
        help=f"faster-whisper compute type. Default: {TRANSCRIPTION_DEFAULTS.compute_type}",
    )
    parser.add_argument(
        "--cpu-threads",
        type=int,
        default=TRANSCRIPTION_DEFAULTS.cpu_threads,
        help=(
            "CPU threads for faster-whisper. "
            f"Default: {TRANSCRIPTION_DEFAULTS.cpu_threads} (all cores)"
        ),
    )
    parser.add_argument(
        "--beam-size",
        type=int,
        default=TRANSCRIPTION_DEFAULTS.beam_size,
        help=f"Beam size for faster-whisper. Default: {TRANSCRIPTION_DEFAULTS.beam_size}",
    )
    parser.add_argument(
        "--language",
        default=TRANSCRIPTION_DEFAULTS.language,
        help=f"Language for faster-whisper. Default: {TRANSCRIPTION_DEFAULTS.language}",
    )
    parser.add_argument(
        "--no-vad-filter",
        action="store_false",
        dest="vad_filter",
        default=TRANSCRIPTION_DEFAULTS.vad_filter,
        help="Disable faster-whisper VAD silence filtering.",
    )
    parser.add_argument(
        "--condition-on-previous-text",
        action="store_true",
        default=TRANSCRIPTION_DEFAULTS.condition_on_previous_text,
        help="Allow faster-whisper to condition each segment on previous text.",
    )
    parser.add_argument(
        "--endpoint",
        default=TRANSCRIPTION_DEFAULTS.endpoint,
        help=f"Deepgram Flux WebSocket endpoint. Default: {TRANSCRIPTION_DEFAULTS.endpoint}",
    )
    parser.add_argument(
        "--api-key-env",
        default=TRANSCRIPTION_DEFAULTS.api_key_env,
        help=f"Environment variable containing the Deepgram API key. Default: {TRANSCRIPTION_DEFAULTS.api_key_env}",
    )
    parser.add_argument(
        "--chunk-ms",
        type=int,
        default=TRANSCRIPTION_DEFAULTS.chunk_ms,
        help=f"Audio chunk size sent to Flux in milliseconds. Default: {TRANSCRIPTION_DEFAULTS.chunk_ms}",
    )
    parser.add_argument(
        "--close-timeout",
        type=float,
        default=TRANSCRIPTION_DEFAULTS.close_timeout_seconds,
        help=(
            "Seconds to wait for final Deepgram messages after sending CloseStream. "
            f"Default: {TRANSCRIPTION_DEFAULTS.close_timeout_seconds}"
        ),
    )
    parser.add_argument(
        "--language-hint",
        action="append",
        default=[],
        help=(
            "Optional language hint for model=flux-general-multi. "
            "May be passed multiple times. Do not use with flux-general-en."
        ),
    )
    parser.add_argument(
        "--no-paste",
        action="store_true",
        help="Only copy to clipboard; do not attempt active-window paste.",
    )
    parser.add_argument(
        "--paste-shortcut",
        default=INSERTION_DEFAULTS.paste_shortcut,
        help=f"X11 paste shortcut for xdotool. Default: {INSERTION_DEFAULTS.paste_shortcut}",
    )
    parser.add_argument(
        "--log-level",
        default="info",
        choices=("debug", "info", "warning", "error"),
        help="Daemon log level. Default: info",
    )
    parser.add_argument(
        "--no-notify",
        action="store_true",
        help="Disable desktop notifications from the daemon.",
    )
    add_vocabulary_arguments(parser)
    return parser


def build_service_parser(prog: str, *, add_help: bool = True) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=prog,
        description="Install and control the Voice Codex user background service.",
        add_help=add_help,
    )
    subparsers = parser.add_subparsers(dest="service_command", required=True)

    install_parser = subparsers.add_parser("install", help="Install the user systemd service.")
    install_parser.add_argument(
        "--working-directory",
        type=Path,
        default=Path.cwd(),
        help="Working directory for the daemon service. Default: current directory.",
    )
    install_parser.add_argument(
        "--log-level",
        default="info",
        choices=("debug", "info", "warning", "error"),
        help="Daemon log level for the service. Default: info",
    )
    install_parser.add_argument(
        "--enable",
        action="store_true",
        help="Enable the service to start on login after installing.",
    )
    install_parser.add_argument(
        "--start",
        action="store_true",
        help="Start the service after installing.",
    )
    install_parser.add_argument(
        "daemon_args",
        nargs=argparse.REMAINDER,
        help="Optional daemon args after --, for example: -- --hotkey '<ctrl>+<alt>+r'",
    )

    subparsers.add_parser("start", help="Start the user service.")
    subparsers.add_parser("stop", help="Stop the user service.")
    subparsers.add_parser("restart", help="Restart the user service.")
    subparsers.add_parser("enable", help="Enable service start on login.")
    subparsers.add_parser("disable", help="Disable service start on login.")
    subparsers.add_parser("status", help="Show service status.")
    logs_parser = subparsers.add_parser("logs", help="Show recent service logs.")
    logs_parser.add_argument("--lines", type=int, default=80, help="Number of log lines.")
    return parser


def run_service_command(args: argparse.Namespace) -> int:
    try:
        command = args.service_command
        if command == "install":
            daemon_args = tuple(arg for arg in args.daemon_args if arg != "--")
            result = install_service(
                working_directory=args.working_directory.expanduser().resolve(),
                log_level=args.log_level,
                extra_args=daemon_args,
            )
            print(f"Installed user service: {result.service_path}")
            if args.enable:
                enable_service()
                print("Enabled service start on login.")
            if args.start:
                start_service()
                print("Started voice-codexd.service.")
            return 0

        if command == "start":
            start_service()
            print("Started voice-codexd.service.")
            return 0

        if command == "stop":
            stop_service()
            print("Stopped voice-codexd.service.")
            return 0

        if command == "restart":
            restart_service()
            print("Restarted voice-codexd.service.")
            return 0

        if command == "enable":
            enable_service()
            print("Enabled voice-codexd.service.")
            return 0

        if command == "disable":
            disable_service()
            print("Disabled voice-codexd.service.")
            return 0

        if command == "status":
            print(service_status())
            return 0

        if command == "logs":
            print(service_logs(lines=args.lines))
            return 0
    except ServiceError as exc:
        print(f"Service error: {exc}", file=sys.stderr)
        return 2

    print(f"Unknown service command: {args.service_command}", file=sys.stderr)
    return 2


def add_vocabulary_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--no-vocabulary",
        action="store_true",
        help="Disable vocabulary files and deterministic correction rules.",
    )
    parser.add_argument(
        "--vocab-file",
        type=Path,
        default=VOCABULARY_DEFAULTS.vocab_file,
        help=f"Vocabulary terms file. Default: {VOCABULARY_DEFAULTS.vocab_file}",
    )
    parser.add_argument(
        "--corrections-file",
        type=Path,
        default=VOCABULARY_DEFAULTS.corrections_file,
        help=f"TOML correction rules file. Default: {VOCABULARY_DEFAULTS.corrections_file}",
    )


def run_once(args: argparse.Namespace) -> int:
    input_device = _coerce_input_device(args.input_device)

    if args.audio_output:
        audio_path = args.audio_output
        temp_dir: tempfile.TemporaryDirectory[str] | None = None
    elif args.keep_audio:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        audio_path = Path.cwd() / f"voice-codex-once-{timestamp}.wav"
        temp_dir = None
    else:
        temp_dir = tempfile.TemporaryDirectory(prefix="voice-codex-")
        audio_path = Path(temp_dir.name) / "voice-codex-once.wav"

    try:
        print(
            "Recording "
            f"{args.duration:.1f}s at {args.sample_rate} Hz "
            f"({args.channels} channel{'s' if args.channels != 1 else ''})...",
            flush=True,
        )
        record_to_wav(
            audio_path,
            duration_seconds=args.duration,
            sample_rate=args.sample_rate,
            channels=args.channels,
            input_device=input_device,
        )
        print(f"Recorded audio: {audio_path}", flush=True)

        print(_transcription_start_message(args), flush=True)
        transcription = transcribe_audio(
            audio_path,
            engine=args.engine,
            model_name=args.model,
            sample_rate=args.sample_rate,
            api_key_env=args.api_key_env,
            endpoint=args.endpoint,
            chunk_ms=args.chunk_ms,
            language_hints=tuple(args.language_hint),
            close_timeout_seconds=args.close_timeout,
            device=args.device,
            compute_type=args.compute_type,
            cpu_threads=args.cpu_threads,
            beam_size=args.beam_size,
            language=args.language,
            vad_filter=args.vad_filter,
            condition_on_previous_text=args.condition_on_previous_text,
        )

        if not transcription.text:
            print("No speech text was detected.", file=sys.stderr)
            return 3

        vocabulary = apply_vocabulary(
            transcription.text,
            _vocabulary_config_from_args(args),
        )

        print(
            "Transcription complete: "
            f"{len(vocabulary.text)} chars, "
            f"{transcription.event_count} {_transcription_count_label(transcription.engine)}, "
            f"{transcription.elapsed_seconds:.2f}s."
        )
        if vocabulary.correction_count:
            print(f"Applied {vocabulary.correction_count} vocabulary corrections.")

        if not args.no_echo:
            print("")
            print("Transcript:")
            print(vocabulary.text)
            print("")

        try:
            insertion = insert_text(
                vocabulary.text,
                paste=not args.no_paste,
                paste_shortcut=args.paste_shortcut,
            )
        except InsertionError as exc:
            print(f"Insertion failed: {exc}", file=sys.stderr)
            print("The transcript was printed above so you can copy it manually.")
            return 4

        print(insertion.message)
        if insertion.insertion_mode == "clipboard-only":
            print("Paste manually into Codex CLI, then press Enter when ready.")
        else:
            print("Review the inserted Codex prompt, then press Enter when ready.")

        return 0
    except (RecordingError, TranscriptionError, VocabularyError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    finally:
        if args.audio_output or args.keep_audio:
            print(f"Kept audio file: {audio_path}")
        elif temp_dir is not None:
            temp_dir.cleanup()


def _coerce_input_device(value: str | None) -> int | str | None:
    if value is None:
        return None

    try:
        return int(value)
    except ValueError:
        return value


def _daemon_options_from_args(args: argparse.Namespace) -> DaemonOptions:
    return DaemonOptions(
        hotkey=args.hotkey,
        max_duration_seconds=args.max_duration,
        keep_audio=args.keep_audio,
        notifications_enabled=not args.no_notify,
        sample_rate=args.sample_rate,
        channels=args.channels,
        input_device=_coerce_input_device(args.input_device),
        engine=args.engine,
        model_name=args.model,
        device=args.device,
        compute_type=args.compute_type,
        cpu_threads=args.cpu_threads,
        beam_size=args.beam_size,
        language=args.language,
        vad_filter=args.vad_filter,
        condition_on_previous_text=args.condition_on_previous_text,
        endpoint=args.endpoint,
        api_key_env=args.api_key_env,
        chunk_ms=args.chunk_ms,
        close_timeout_seconds=args.close_timeout,
        language_hints=tuple(args.language_hint),
        paste=not args.no_paste,
        paste_shortcut=args.paste_shortcut,
        audio_dir=args.audio_dir,
        vocabulary_enabled=not args.no_vocabulary,
        vocab_file=args.vocab_file,
        corrections_file=args.corrections_file,
    )


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def _transcription_start_message(args: argparse.Namespace) -> str:
    if args.engine == "faster-whisper":
        return (
            "Transcribing with faster-whisper "
            f"model={args.model} device={args.device} "
            f"compute_type={args.compute_type} beam_size={args.beam_size}..."
        )

    return (
        "Transcribing with Deepgram Flux "
        f"model={args.model} endpoint={args.endpoint} "
        f"chunk_ms={args.chunk_ms}..."
    )


def _transcription_count_label(engine: str) -> str:
    return "segments" if engine == "faster-whisper" else "Deepgram events"


def _vocabulary_config_from_args(args: argparse.Namespace) -> VocabularyConfig:
    return VocabularyConfig(
        enabled=not args.no_vocabulary,
        vocab_file=args.vocab_file,
        corrections_file=args.corrections_file,
    )


if __name__ == "__main__":
    raise SystemExit(main())
