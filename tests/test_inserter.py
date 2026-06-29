from __future__ import annotations

import subprocess
import unittest
from unittest.mock import Mock, patch

from voice_codex.inserter import (
    YdotoolStatus,
    _copy_with_wl_copy,
    command_path,
    insert_text,
    paste_into_active_window,
    paste_with_ydotool,
    type_with_ydotool,
    ydotool_ready,
)


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

    def test_paste_with_ydotool_returns_false_when_missing(self) -> None:
        with patch("voice_codex.inserter.command_path", return_value=None):
            self.assertFalse(paste_with_ydotool())

    def test_paste_with_ydotool_runs_ctrl_shift_v(self) -> None:
        with patch("voice_codex.inserter.command_path", return_value="/usr/bin/ydotool"), patch(
            "voice_codex.inserter.ydotool_status",
            return_value=YdotoolStatus(True, "ydotoold socket is ready at /tmp/.ydotool_socket"),
        ), patch(
            "voice_codex.inserter.subprocess.run"
        ) as run:
            self.assertTrue(paste_with_ydotool())

        run.assert_called_once()
        command = run.call_args.args[0]
        self.assertEqual(command[:2], ["/usr/bin/ydotool", "key"])
        self.assertIn("29:1", command)
        self.assertIn("47:1", command)

    def test_unknown_session_uses_ydotool_when_socket_is_ready(self) -> None:
        with patch(
            "voice_codex.inserter.ydotool_status",
            return_value=YdotoolStatus(True, "ydotoold socket is ready at /tmp/.ydotool_socket"),
        ), patch("voice_codex.inserter.type_with_ydotool", return_value=True) as type_text:
            self.assertTrue(
                paste_into_active_window(
                    text="hello",
                    paste_shortcut="ctrl+shift+v",
                    session_type="unknown",
                )
            )

        type_text.assert_called_once_with("hello")

    def test_type_with_ydotool_uses_stdin_file_and_normalizes_newlines(self) -> None:
        with patch("voice_codex.inserter.command_path", return_value="/usr/bin/ydotool"), patch(
            "voice_codex.inserter.ydotool_status",
            return_value=YdotoolStatus(True, "ydotoold socket is ready at /tmp/.ydotool_socket"),
        ), patch(
            "voice_codex.inserter.subprocess.run"
        ) as run:
            self.assertTrue(type_with_ydotool("hello\nworld"))

        run.assert_called_once()
        command = run.call_args.args[0]
        self.assertEqual(command[:2], ["/usr/bin/ydotool", "type"])
        self.assertIn("--file", command)
        self.assertEqual(run.call_args.kwargs["input"], b"hello world")

    def test_unknown_session_success_reports_ydotool_type_mode(self) -> None:
        with patch("voice_codex.inserter.copy_to_clipboard", return_value="wl-copy"), patch(
            "voice_codex.inserter.paste_into_active_window",
            return_value=True,
        ):
            result = insert_text(
                "hello",
                paste=True,
                paste_shortcut="ctrl+shift+v",
                session_type="unknown",
            )

        self.assertEqual(result.insertion_mode, "ydotool-type")
        self.assertTrue(result.pasted)

    def test_command_path_falls_back_to_common_absolute_paths(self) -> None:
        with patch("voice_codex.inserter.shutil.which", return_value=None), patch(
            "voice_codex.inserter.Path.exists", return_value=True
        ), patch("voice_codex.inserter.os.access", return_value=True):
            self.assertEqual(command_path("wl-copy"), "/usr/bin/wl-copy")

    def test_ydotool_ready_requires_socket(self) -> None:
        with patch("voice_codex.inserter.command_path", return_value="/usr/bin/ydotool"), patch(
            "voice_codex.inserter.Path.is_socket", return_value=False
        ):
            self.assertFalse(ydotool_ready())

    def test_ydotool_ready_accepts_existing_socket(self) -> None:
        with patch("voice_codex.inserter.command_path", return_value="/usr/bin/ydotool"), patch(
            "voice_codex.inserter.Path.is_socket", return_value=True
        ), patch("voice_codex.inserter.os.access", return_value=True):
            self.assertTrue(ydotool_ready())

    def test_ydotool_ready_rejects_unusable_socket(self) -> None:
        with patch("voice_codex.inserter.command_path", return_value="/usr/bin/ydotool"), patch(
            "voice_codex.inserter.Path.is_socket", return_value=True
        ), patch("voice_codex.inserter.os.access", return_value=False):
            self.assertFalse(ydotool_ready())


if __name__ == "__main__":
    unittest.main()
