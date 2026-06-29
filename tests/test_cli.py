from __future__ import annotations

import unittest

from voice_codex.cli import (
    _coerce_input_device,
    _daemon_options_from_args,
    build_daemon_parser,
    build_service_parser,
)


class CliTests(unittest.TestCase):
    def test_coerce_numeric_input_device(self) -> None:
        self.assertEqual(_coerce_input_device("3"), 3)

    def test_keep_named_input_device(self) -> None:
        self.assertEqual(_coerce_input_device("USB Microphone"), "USB Microphone")

    def test_empty_input_device_stays_none(self) -> None:
        self.assertIsNone(_coerce_input_device(None))

    def test_daemon_parser_builds_options(self) -> None:
        parser = build_daemon_parser("voice-codex-daemon")
        args = parser.parse_args(
            [
                "--hotkey",
                "ctrl+alt+r",
                "--max-duration",
                "12",
                "--input-device",
                "4",
                "--model",
                "small.en",
                "--compute-type",
                "int8",
                "--beam-size",
                "1",
                "--no-paste",
                "--language-hint",
                "en",
                "--no-vocabulary",
                "--no-notify",
            ]
        )

        options = _daemon_options_from_args(args)

        self.assertEqual(options.hotkey, "ctrl+alt+r")
        self.assertEqual(options.max_duration_seconds, 12)
        self.assertEqual(options.input_device, 4)
        self.assertEqual(options.engine, "faster-whisper")
        self.assertEqual(options.model_name, "small.en")
        self.assertEqual(options.compute_type, "int8")
        self.assertEqual(options.beam_size, 1)
        self.assertEqual(options.language, "en")
        self.assertTrue(options.vad_filter)
        self.assertFalse(options.condition_on_previous_text)
        self.assertFalse(options.paste)
        self.assertEqual(options.language_hints, ("en",))
        self.assertFalse(options.vocabulary_enabled)
        self.assertFalse(options.notifications_enabled)

    def test_service_parser_install_command(self) -> None:
        parser = build_service_parser("voice-codex-service")
        args = parser.parse_args(
            [
                "install",
                "--log-level",
                "debug",
                "--enable",
                "--start",
                "--",
                "--hotkey",
                "<ctrl>+<alt>+r",
            ]
        )

        self.assertEqual(args.service_command, "install")
        self.assertEqual(args.log_level, "debug")
        self.assertTrue(args.enable)
        self.assertTrue(args.start)
        self.assertEqual(args.daemon_args, ["--", "--hotkey", "<ctrl>+<alt>+r"])


if __name__ == "__main__":
    unittest.main()
