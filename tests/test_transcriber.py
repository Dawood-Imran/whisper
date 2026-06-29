from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from voice_codex.transcriber import build_flux_url, parse_flux_message, transcribe_audio


class FasterWhisperTranscriberTests(unittest.TestCase):
    def test_transcribe_audio_uses_faster_whisper_defaults(self) -> None:
        first_segment = Mock()
        first_segment.text = " hello "
        second_segment = Mock()
        second_segment.text = "codex"
        model = Mock()
        model.transcribe.return_value = ([first_segment, second_segment], object())

        with patch("voice_codex.transcriber.get_faster_whisper_model", return_value=model):
            result = transcribe_audio(
                "prompt.wav",  # type: ignore[arg-type]
                engine="faster-whisper",
                model_name="small.en",
                beam_size=1,
                language="en",
                vad_filter=True,
                condition_on_previous_text=False,
            )

        self.assertEqual(result.text, "hello codex")
        self.assertEqual(result.engine, "faster-whisper")
        self.assertEqual(result.model, "small.en")
        self.assertEqual(result.event_count, 2)
        model.transcribe.assert_called_once_with(
            "prompt.wav",
            beam_size=1,
            language="en",
            vad_filter=True,
            condition_on_previous_text=False,
        )


class DeepgramFluxTranscriberTests(unittest.TestCase):
    def test_build_flux_url_uses_v2_listen_and_linear16(self) -> None:
        url = build_flux_url(
            endpoint="wss://api.deepgram.com/v2/listen",
            model_name="flux-general-en",
            sample_rate=16000,
        )

        self.assertEqual(
            url,
            "wss://api.deepgram.com/v2/listen"
            "?model=flux-general-en&encoding=linear16&sample_rate=16000",
        )

    def test_build_flux_url_rejects_v1_endpoint(self) -> None:
        with self.assertRaises(ValueError):
            build_flux_url(
                endpoint="wss://api.deepgram.com/v1/listen",
                model_name="flux-general-en",
                sample_rate=16000,
            )

    def test_language_hints_require_multilingual_model(self) -> None:
        with self.assertRaises(ValueError):
            build_flux_url(
                endpoint="wss://api.deepgram.com/v2/listen",
                model_name="flux-general-en",
                sample_rate=16000,
                language_hints=("en",),
            )

    def test_language_hints_are_repeated_for_multilingual_model(self) -> None:
        url = build_flux_url(
            endpoint="wss://api.deepgram.com/v2/listen",
            model_name="flux-general-multi",
            sample_rate=16000,
            language_hints=("en", "es"),
        )

        self.assertIn("model=flux-general-multi", url)
        self.assertIn("language_hint=en", url)
        self.assertIn("language_hint=es", url)

    def test_parse_turn_info_message(self) -> None:
        message = parse_flux_message(
            '{"type":"TurnInfo","turn_index":2,"transcript":"hello codex"}'
        )

        self.assertIsNotNone(message)
        assert message is not None
        self.assertEqual(message.type, "TurnInfo")
        self.assertEqual(message.turn_index, 2)
        self.assertEqual(message.transcript, "hello codex")

    def test_parse_binary_message_returns_none(self) -> None:
        self.assertIsNone(parse_flux_message(b"binary"))


if __name__ == "__main__":
    unittest.main()
