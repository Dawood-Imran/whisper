from __future__ import annotations

import subprocess
import unittest
from unittest.mock import patch

from voice_codex.notify import notify_user


class NotifyTests(unittest.TestCase):
    def test_notify_returns_false_when_missing(self) -> None:
        with patch("voice_codex.notify.shutil.which", return_value=None):
            self.assertFalse(notify_user("Hello"))

    def test_notify_runs_notify_send(self) -> None:
        with patch("voice_codex.notify.shutil.which", return_value="/usr/bin/notify-send"), patch(
            "voice_codex.notify.subprocess.run"
        ) as run:
            self.assertTrue(notify_user("Recording started", "Press F9 again."))

        command = run.call_args.args[0]
        self.assertIn("notify-send", command)
        self.assertIn("Recording started", command)

    def test_notify_failure_returns_false(self) -> None:
        with patch("voice_codex.notify.shutil.which", return_value="/usr/bin/notify-send"), patch(
            "voice_codex.notify.subprocess.run",
            side_effect=subprocess.CalledProcessError(1, ["notify-send"]),
        ):
            self.assertFalse(notify_user("Hello"))


if __name__ == "__main__":
    unittest.main()
