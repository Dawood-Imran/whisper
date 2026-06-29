from __future__ import annotations

import unittest
from pathlib import Path

from voice_codex.service import build_service_file


class ServiceTests(unittest.TestCase):
    def test_build_service_file_uses_python_module_daemon(self) -> None:
        content = build_service_file(
            python_executable=Path("/tmp/venv/bin/python"),
            working_directory=Path("/tmp/voice codex"),
            log_level="debug",
            extra_args=("--hotkey", "<ctrl>+<alt>+r"),
        )

        self.assertIn("[Unit]", content)
        self.assertIn("WorkingDirectory=/tmp/voice codex", content)
        self.assertIn('Environment="PATH=', content)
        self.assertIn("EnvironmentFile=-%h/.config/voice-codex/env", content)
        self.assertIn("PassEnvironment=DISPLAY WAYLAND_DISPLAY XDG_RUNTIME_DIR", content)
        self.assertIn("YDOTOOL_SOCKET", content)
        self.assertIn("/tmp/venv/bin/python -m voice_codex daemon", content)
        self.assertIn("--log-level debug", content)
        self.assertIn("--hotkey <ctrl>+<alt>+r", content)


if __name__ == "__main__":
    unittest.main()
