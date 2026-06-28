from __future__ import annotations

import argparse
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from voice_codex.config import (
    INSERTION_DEFAULTS,
    RECORDING_DEFAULTS,
    TRANSCRIPTION_DEFAULTS,
)
from voice_codex.inserter import InsertionError, insert_text
from voice_codex.preflight import format_report, run_preflight
from voice_codex.recorder import RecordingError, record_to_wav
from voice_codex.transcriber import TranscriptionError, transcribe_audio


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="voice-codex",
        description="Voice Codex Phase 1 command-line tools.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser(
        "preflight",
        help="Check whether this machine is ready for Phase 1.",
    )

    once_parser = build_once_parser("voice-codex once", add_help=False)
    subparsers.add_parser(
        "once",
        parents=[once_parser],
        add_help=True,
        help="Record, transcribe, and copy or insert one spoken prompt.",
    )

    args = parser.parse_args(argv)

    if args.command == "preflight":
        return preflight_main([])

    if args.command == "once":
        return run_once(args)

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
        "--model",
        default=TRANSCRIPTION_DEFAULTS.model,
        help=f"Deepgram Flux model name. Default: {TRANSCRIPTION_DEFAULTS.model}",
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
    return parser


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

        print(
            "Transcribing with Deepgram Flux "
            f"model={args.model} endpoint={args.endpoint} "
            f"chunk_ms={args.chunk_ms}...",
            flush=True,
        )
        transcription = transcribe_audio(
            audio_path,
            model_name=args.model,
            sample_rate=args.sample_rate,
            api_key_env=args.api_key_env,
            endpoint=args.endpoint,
            chunk_ms=args.chunk_ms,
            language_hints=tuple(args.language_hint),
            close_timeout_seconds=args.close_timeout,
        )

        if not transcription.text:
            print("No speech text was detected.", file=sys.stderr)
            return 3

        print(
            "Transcription complete: "
            f"{len(transcription.text)} chars, "
            f"{transcription.event_count} Deepgram events, "
            f"{transcription.elapsed_seconds:.2f}s."
        )

        if not args.no_echo:
            print("")
            print("Transcript:")
            print(transcription.text)
            print("")

        try:
            insertion = insert_text(
                transcription.text,
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
    except (RecordingError, TranscriptionError, ValueError) as exc:
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


if __name__ == "__main__":
    raise SystemExit(main())
