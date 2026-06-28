from __future__ import annotations

import subprocess
import unittest
from unittest.mock import Mock, patch

from voice_codex.inserter import _copy_with_wl_copy


class InserterTests(unittest.TestCase):
    def test_wl_copy_timeout_is_treated_as_background_clipboard_owner(self) -> None:
        process = Mock()
        process.stdin = Mock()
        process.stderr = Mock()
        process.wait.side_effect = subprocess.TimeoutExpired(["wl-copy"], timeout=0.2)

        with patch("voice_codex.inserter.subprocess.Popen", return_value=process):
            _copy_with_wl_copy("hello")

        process.stdin.write.assert_called_once_with(b"hello")
        process.stdin.close.assert_called_once()

    def test_wl_copy_nonzero_exit_raises(self) -> None:
        process = Mock()
        process.stdin = Mock()
        process.stderr.read.return_value = b"copy failed"
        process.wait.return_value = 1

        with patch("voice_codex.inserter.subprocess.Popen", return_value=process):
            with self.assertRaises(RuntimeError):
                _copy_with_wl_copy("hello")


if __name__ == "__main__":
    unittest.main()
