"""Non-LLM Post-Validation Layer for Error Analysis.

RESEARCH INTEGRITY RULES:
1. Span must exactly match the transcript text at the given offsets (reject hallucinated spans).
2. Category must exist in the active rubric version taxonomy.
3. No overlapping duplicate annotations for the same category.
4. Proposed correction must differ from candidate span.
5. Acoustic timestamps interpolated from word timestamps if omitted.
"""

import json
import logging
from typing import Any

from app.services.llm.base import AnnotationItem

logger = logging.getLogger(__name__)

VALID_RUBRIC_CATEGORIES = frozenset({"TNS", "SVA", "WO", "AUX", "ART", "PREP", "PRO", "OTH"})


class PostValidationError(Exception):
    """Raised when an annotation violates non-LLM scientific constraints."""
    pass


class PostValidationLayer:
    """Rigorous non-LLM validation and alignment engine."""

    def validate_and_align_annotations(
        self,
        transcript: str,
        annotations: list[AnnotationItem],
        words_json: str | None = None,
        allowed_categories: set[str] | frozenset[str] = VALID_RUBRIC_CATEGORIES,
    ) -> list[AnnotationItem]:
        """Validate, deduplicate, and timestamp candidate error annotations."""
        validated: list[AnnotationItem] = []
        words_data: list[dict[str, Any]] = []

        if words_json:
            try:
                words_data = json.loads(words_json)
            except Exception:
                words_data = []

        for ann in annotations:
            # 1. Category validation
            if ann.category_code not in allowed_categories:
                logger.warning(
                    "Rejecting annotation: category '%s' not in rubric taxonomy.",
                    ann.category_code,
                )
                continue

            # 2. Correction must differ from candidate span
            if ann.proposed_correction.strip().lower() == ann.span_text.strip().lower():
                logger.warning(
                    "Rejecting annotation: proposed correction '%s' identical to span '%s'.",
                    ann.proposed_correction,
                    ann.span_text,
                )
                continue

            # 3. Span Offset Alignment & Hallucination Check
            span_len = len(ann.span_text)
            char_start = ann.char_start
            char_end = ann.char_end

            # Check if offsets are valid within transcript boundaries
            if char_end > len(transcript) or char_start < 0 or char_start >= char_end:
                # Attempt to locate span in transcript
                found_idx = transcript.find(ann.span_text)
                if found_idx == -1:
                    logger.warning("Rejecting hallucinated span: '%s' not found in transcript.", ann.span_text)
                    continue
                char_start = found_idx
                char_end = found_idx + span_len

            actual_substring = transcript[char_start:char_end]

            # If mismatch, attempt tolerance search within ±5 characters
            if actual_substring != ann.span_text:
                matched = False
                for shift in range(-5, 6):
                    test_start = char_start + shift
                    test_end = test_start + span_len
                    if 0 <= test_start < test_end <= len(transcript):
                        if transcript[test_start:test_end] == ann.span_text:
                            char_start = test_start
                            char_end = test_end
                            matched = True
                            break
                if not matched:
                    # Final check: search for exact span occurrence in transcript
                    loc = transcript.find(ann.span_text)
                    if loc != -1:
                        char_start = loc
                        char_end = loc + span_len
                    else:
                        logger.warning(
                            "Rejecting hallucinated span: transcript[%d:%d]='%s' != span_text='%s'",
                            char_start,
                            char_end,
                            actual_substring,
                            ann.span_text,
                        )
                        continue

            # 4. Interpolate Acoustic Timestamps if omitted
            time_start = ann.time_start
            time_end = ann.time_end

            if (time_start is None or time_end is None) and words_data:
                # Find matching word in words_data
                for w in words_data:
                    word_str = w.get("word", "").strip(".,!?:;\"'")
                    if word_str.lower() in ann.span_text.lower():
                        if time_start is None:
                            time_start = float(w.get("start", 0.0))
                        time_end = float(w.get("end", time_start + 0.5))

            updated_ann = ann.model_copy(
                update={
                    "char_start": char_start,
                    "char_end": char_end,
                    "time_start": time_start,
                    "time_end": time_end,
                }
            )
            validated.append(updated_ann)

        # 5. Deduplicate overlapping annotations within the same category
        # Sort by char_start, then by confidence descending
        validated.sort(key=lambda a: (a.char_start, -a.confidence))
        deduped: list[AnnotationItem] = []

        for item in validated:
            overlap = False
            for existing in deduped:
                # Check same category and span overlap
                if existing.category_code == item.category_code:
                    if not (item.char_end <= existing.char_start or item.char_start >= existing.char_end):
                        overlap = True
                        break
            if not overlap:
                deduped.append(item)

        return deduped


post_validator = PostValidationLayer()
