from __future__ import annotations

import unittest

from voice_codex.cli import _coerce_input_device


class CliTests(unittest.TestCase):
    def test_coerce_numeric_input_device(self) -> None:
        self.assertEqual(_coerce_input_device("3"), 3)

    def test_keep_named_input_device(self) -> None:
        self.assertEqual(_coerce_input_device("USB Microphone"), "USB Microphone")

    def test_empty_input_device_stays_none(self) -> None:
        self.assertIsNone(_coerce_input_device(None))


if __name__ == "__main__":
    unittest.main()
