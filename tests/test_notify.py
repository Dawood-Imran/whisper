from __future__ import annotations

import unittest
from unittest.mock import patch

from voice_codex.notify import notify_user


class NotifyTests(unittest.TestCase):
    def test_notify_returns_false_when_missing(self) -> None:
        with patch("voice_codex.notify.shutil.which", return_value=None):
            self.assertFalse(notify_user("Hello"))

    def test_notify_runs_notify_send(self) -> None:
        with patch("voice_codex.notify.shutil.which", return_value="/usr/bin/notify-send"), patch(
            "voice_codex.notify.subprocess.Popen"
        ) as popen:
            self.assertTrue(notify_user("Recording started", "Press Ctrl+Alt+Space again."))

        command = popen.call_args.args[0]
        self.assertIn("notify-send", command)
        self.assertIn("Recording started", command)

    def test_notify_failure_returns_false(self) -> None:
        with patch("voice_codex.notify.shutil.which", return_value="/usr/bin/notify-send"), patch(
            "voice_codex.notify.subprocess.Popen",
            side_effect=OSError("notify failed"),
        ):
            self.assertFalse(notify_user("Hello"))


if __name__ == "__main__":
    unittest.main()
