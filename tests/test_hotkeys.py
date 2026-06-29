from __future__ import annotations

import unittest

from voice_codex.hotkeys import normalize_hotkey, session_warns_for_hotkeys


class HotkeyTests(unittest.TestCase):
    def test_normalize_common_modifier_names(self) -> None:
        self.assertEqual(normalize_hotkey("ctrl+alt+r"), "<ctrl>+<alt>+r")
        self.assertEqual(normalize_hotkey("ctrl+alt+space"), "<ctrl>+<alt>+<space>")

    def test_normalize_preserves_angle_bracket_modifiers(self) -> None:
        self.assertEqual(normalize_hotkey("<ctrl>+<shift>+space"), "<ctrl>+<shift>+<space>")

    def test_empty_hotkey_is_invalid(self) -> None:
        with self.assertRaises(ValueError):
            normalize_hotkey("  ")

    def test_wayland_session_reports_warning(self) -> None:
        warning = session_warns_for_hotkeys("wayland")

        self.assertIsNotNone(warning)
        assert warning is not None
        self.assertIn("Wayland", warning)

    def test_x11_session_has_no_hotkey_warning(self) -> None:
        self.assertIsNone(session_warns_for_hotkeys("x11"))


if __name__ == "__main__":
    unittest.main()
