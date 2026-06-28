from __future__ import annotations

import unittest

from voice_codex.preflight import (
    ToolCheck,
    choose_clipboard_backend,
    choose_insertion_mode,
)


class PreflightSelectionTests(unittest.TestCase):
    def test_wayland_prefers_wl_copy(self) -> None:
        tools = (
            ToolCheck("wl-copy", "/usr/bin/wl-copy"),
            ToolCheck("xclip", "/usr/bin/xclip"),
        )

        self.assertEqual(choose_clipboard_backend("wayland", tools), "wl-copy")

    def test_x11_prefers_xclip(self) -> None:
        tools = (
            ToolCheck("xclip", "/usr/bin/xclip"),
            ToolCheck("xsel", "/usr/bin/xsel"),
        )

        self.assertEqual(choose_clipboard_backend("x11", tools), "xclip")

    def test_x11_paste_requires_clipboard_and_xdotool(self) -> None:
        tools = (
            ToolCheck("xclip", "/usr/bin/xclip"),
            ToolCheck("xdotool", "/usr/bin/xdotool"),
        )

        self.assertEqual(choose_insertion_mode("x11", tools, "xclip"), "x11-paste")

    def test_clipboard_only_when_no_direct_paste(self) -> None:
        tools = (ToolCheck("wl-copy", "/usr/bin/wl-copy"),)

        self.assertEqual(
            choose_insertion_mode("wayland", tools, "wl-copy"),
            "clipboard-only",
        )

    def test_insertion_unavailable_without_clipboard(self) -> None:
        tools = (ToolCheck("ffmpeg", "/usr/bin/ffmpeg"),)

        self.assertEqual(choose_insertion_mode("unknown", tools, None), "unavailable")


if __name__ == "__main__":
    unittest.main()
