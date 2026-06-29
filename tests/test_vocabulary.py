from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from voice_codex.vocabulary import (
    VocabularyConfig,
    apply_corrections,
    apply_vocabulary,
    load_corrections,
    load_vocabulary_terms,
)


class VocabularyTests(unittest.TestCase):
    def test_missing_files_are_empty(self) -> None:
        missing = Path("/tmp/voice-codex-missing-vocabulary-test")

        self.assertEqual(load_vocabulary_terms(missing), ())
        self.assertEqual(load_corrections(missing), {})

    def test_load_vocabulary_terms_skips_comments_and_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "vocabulary.txt"
            path.write_text("# comment\nDawood\nCodex\ndawood\n\n", encoding="utf-8")

            self.assertEqual(load_vocabulary_terms(path), ("Dawood", "Codex"))

    def test_load_corrections_from_toml(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "corrections.toml"
            path.write_text(
                '[corrections]\n"the wood" = "Dawood"\n"j w t" = "JWT"\n',
                encoding="utf-8",
            )

            self.assertEqual(
                load_corrections(path),
                {"the wood": "Dawood", "j w t": "JWT"},
            )

    def test_apply_corrections_is_case_insensitive_and_boundary_safe(self) -> None:
        corrected, applied = apply_corrections(
            "ask the wood about fast api but not breakfast api",
            {"the wood": "Dawood", "fast api": "FastAPI"},
        )

        self.assertEqual(corrected, "ask Dawood about FastAPI but not breakfast api")
        self.assertEqual(applied, (("the wood", "Dawood", 1), ("fast api", "FastAPI", 1)))

    def test_apply_vocabulary_can_be_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            corrections = Path(temp_dir) / "corrections.toml"
            corrections.write_text('[corrections]\n"the wood" = "Dawood"\n', encoding="utf-8")

            result = apply_vocabulary(
                "hello the wood",
                VocabularyConfig(
                    enabled=False,
                    vocab_file=Path(temp_dir) / "vocabulary.txt",
                    corrections_file=corrections,
                ),
            )

            self.assertEqual(result.text, "hello the wood")
            self.assertEqual(result.correction_count, 0)


if __name__ == "__main__":
    unittest.main()
