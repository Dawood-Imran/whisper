from __future__ import annotations

import unittest

from voice_codex.cli import _coerce_input_device, _daemon_options_from_args, build_daemon_parser


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
                "--no-paste",
                "--language-hint",
                "en",
            ]
        )

        options = _daemon_options_from_args(args)

        self.assertEqual(options.hotkey, "ctrl+alt+r")
        self.assertEqual(options.max_duration_seconds, 12)
        self.assertEqual(options.input_device, 4)
        self.assertFalse(options.paste)
        self.assertEqual(options.language_hints, ("en",))


if __name__ == "__main__":
    unittest.main()
