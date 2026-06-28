from __future__ import annotations

import unittest

from voice_codex.transcriber import build_flux_url, parse_flux_message


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
