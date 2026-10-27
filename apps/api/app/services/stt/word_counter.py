"""Word-counting engine implementing frozen rubric rules.

RESEARCH RULE (SRS FR-06, FR-08):
Word count must be computed by the frozen word-counting rule from the rubric version:
1. Word Definition: A whitespace-separated sequence of alphabetic characters.
2. Punctuation: Stripped from boundaries before tokenisation.
3. Contractions: Counted as single token according to transcript convention (standard: 'don\'t' = 1 word).
4. Hyphenated Compounds: Counted as a single compound word ('state-of-the-art' = 1 word).
5. Speech Fillers: Excluded from total word denominator ('um', 'uh', 'ah', 'mm', 'er', 'erm').
"""

import re

# Standard speech fillers excluded per rubric spec
DEFAULT_FILLERS = frozenset({"um", "uh", "ah", "mm", "er", "erm", "hmm"})


def count_words(text: str | None, exclude_fillers: bool = True) -> int:
    """Compute faithful research-grade word count from transcript text."""
    if not text or not text.strip():
        return 0

    tokens = text.strip().split()
    valid_word_count = 0

    for token in tokens:
        # Strip leading and trailing punctuation (quotes, brackets, commas, periods, exclamation, etc.)
        # but preserve internal hyphens and apostrophes for compounds and contractions
        cleaned = re.sub(r"^[^\w]+|[^\w]+$", "", token).lower()

        if not cleaned:
            continue

        # Check if it is a speech filler
        if exclude_fillers and cleaned in DEFAULT_FILLERS:
            continue

        # Must contain at least one alphanumeric character
        if any(c.isalnum() for c in cleaned):
            valid_word_count += 1

    return valid_word_count


def tokenize_words(text: str | None, exclude_fillers: bool = True) -> list[str]:
    """Return cleaned tokens according to frozen rubric rules."""
    if not text or not text.strip():
        return []

    tokens = text.strip().split()
    valid_tokens: list[str] = []

    for token in tokens:
        cleaned = re.sub(r"^[^\w]+|[^\w]+$", "", token).lower()
        if not cleaned:
            continue
        if exclude_fillers and cleaned in DEFAULT_FILLERS:
            continue
        if any(c.isalnum() for c in cleaned):
            valid_tokens.append(cleaned)

    return valid_tokens
