from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


class VocabularyError(RuntimeError):
    """Raised when vocabulary or correction files cannot be loaded."""


@dataclass(frozen=True)
class VocabularyConfig:
    enabled: bool
    vocab_file: Path
    corrections_file: Path


@dataclass(frozen=True)
class VocabularyResult:
    text: str
    terms: tuple[str, ...]
    corrections: dict[str, str]
    applied: tuple[tuple[str, str, int], ...]

    @property
    def correction_count(self) -> int:
        return sum(count for _wrong, _correct, count in self.applied)


def apply_vocabulary(text: str, config: VocabularyConfig) -> VocabularyResult:
    if not config.enabled:
        return VocabularyResult(text=text, terms=(), corrections={}, applied=())

    terms = load_vocabulary_terms(config.vocab_file)
    corrections = load_corrections(config.corrections_file)
    corrected_text, applied = apply_corrections(text, corrections)

    return VocabularyResult(
        text=corrected_text,
        terms=terms,
        corrections=corrections,
        applied=applied,
    )


def load_vocabulary_terms(path: Path) -> tuple[str, ...]:
    expanded = path.expanduser()
    if not expanded.exists():
        return ()

    try:
        lines = expanded.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise VocabularyError(f"Could not read vocabulary file '{expanded}': {exc}") from exc

    terms: list[str] = []
    seen: set[str] = set()
    for line in lines:
        term = line.strip()
        if not term or term.startswith("#"):
            continue

        key = term.casefold()
        if key in seen:
            continue

        seen.add(key)
        terms.append(term)

    return tuple(terms)


def load_corrections(path: Path) -> dict[str, str]:
    expanded = path.expanduser()
    if not expanded.exists():
        return {}

    try:
        import tomllib
    except ImportError:
        import tomli as tomllib  # type: ignore[no-redef]

    try:
        data = tomllib.loads(expanded.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise VocabularyError(f"Could not read corrections file '{expanded}': {exc}") from exc

    raw_corrections = data.get("corrections", {})
    if not isinstance(raw_corrections, dict):
        raise VocabularyError(
            f"Corrections file '{expanded}' must contain a [corrections] table."
        )

    corrections: dict[str, str] = {}
    for wrong, correct in raw_corrections.items():
        if not isinstance(wrong, str) or not isinstance(correct, str):
            raise VocabularyError("Correction keys and values must be strings.")

        wrong_text = wrong.strip()
        correct_text = correct.strip()
        if not wrong_text or not correct_text:
            continue

        corrections[wrong_text] = correct_text

    return corrections


def apply_corrections(
    text: str,
    corrections: dict[str, str],
) -> tuple[str, tuple[tuple[str, str, int], ...]]:
    corrected = text
    applied: list[tuple[str, str, int]] = []

    for wrong, correct in sorted(corrections.items(), key=lambda item: len(item[0]), reverse=True):
        pattern = _literal_phrase_pattern(wrong)
        corrected, count = pattern.subn(correct, corrected)
        if count:
            applied.append((wrong, correct, count))

    return corrected, tuple(applied)


def _literal_phrase_pattern(phrase: str) -> re.Pattern[str]:
    escaped = re.escape(phrase)
    return re.compile(rf"(?<![A-Za-z0-9_]){escaped}(?![A-Za-z0-9_])", re.IGNORECASE)
