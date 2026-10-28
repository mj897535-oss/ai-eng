"""Pure Research Metrics Module for SyntaxLens.

CRITICAL RESEARCH INTEGRITY RULE:
All metrics must be computed strictly by this pure, stateless, zero-I/O module.
Formulas must never be re-implemented in the UI or duplicated across database queries.
All calculations match SRS Section 7, Section 14, and approved Signature Features.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum


class ErrorCategory(str, Enum):
    """Standardized 8 syntactic deviation categories per SRS FR-08."""
    TNS = "TNS"    # Tense and aspect
    SVA = "SVA"    # Subject-verb agreement
    WO = "WO"      # Word order
    AUX = "AUX"    # Auxiliary verb usage
    ART = "ART"    # Articles (definite, indefinite, zero)
    PREP = "PREP"  # Prepositions
    PRO = "PRO"    # Pronouns
    OTH = "OTH"    # Other / uncertain / acceptable variation


@dataclass(frozen=True)
class CategoryMetric:
    """Category-level error breakdown with low-count and observation flags."""
    category_code: str
    count: int
    rate_per_100_words: float
    observed: bool
    status_label: str  # e.g., "observed" or "not observed in this sample"


@dataclass(frozen=True)
class AssessmentMetricsResult:
    """Comprehensive metric report for a single assessment."""
    word_count: int
    error_count: int
    overall_error_rate_per_100: float
    category_breakdown: dict[str, CategoryMetric]
    rubric_version: str
    model_version: str
    stt_version: str


@dataclass(frozen=True)
class ComparativeMetricsResult:
    """Pre-to-post comparative report with strict zero-baseline handling."""
    pre_word_count: int
    post_word_count: int
    pre_error_count: int
    post_error_count: int
    pre_rate_per_100: float
    post_rate_per_100: float
    absolute_reduction: float
    relative_reduction_pct: float | None
    relative_reduction_status: str  # "defined" or "undefined_zero_baseline"
    category_comparisons: dict[str, tuple[CategoryMetric, CategoryMetric]]
    scientific_disclaimer: str


@dataclass(frozen=True)
class AgreementMetrics:
    """Inter-reviewer agreement metrics for Reviewer Cockpit (Signature Feature D)."""
    total_items: int
    concordant_items: int
    percent_agreement: float
    cohens_kappa: float | None
    interpretation: str


@dataclass(frozen=True)
class PilotAccuracyMetrics:
    """Pilot Kit transcription & classification evaluation (Signature Feature F)."""
    wer: float  # Word Error Rate
    precision: float
    recall: float
    f1_score: float
    tp: int
    fp: int
    fn: int


def _round_metric(value: float, places: int = 2) -> float:
    """Deterministic rounding to avoid floating-point display artifacts."""
    d = Decimal(str(value))
    return float(d.quantize(Decimal(f"1e-{places}"), rounding=ROUND_HALF_UP))


def count_words(transcript: str) -> int:
    """Compute official word count from transcript.

    Uses a deterministic tokenization rule splitting on whitespace after
    stripping punctuation. Hyphenated compound words count as 1 word.
    """
    if not transcript or not transcript.strip():
        return 0
    # Match alphanumeric token sequences (including internal apostrophes/hyphens)
    words = re.findall(r"\b[\w'-]+\b", transcript.strip())
    return len(words)


def calculate_error_rate(error_count: int, word_count: int) -> float:
    """Calculate error rate per 100 words.

    Formula: (error_count / word_count) * 100.
    Returns 0.0 if word_count is 0.
    """
    if word_count <= 0:
        return 0.0
    raw_rate = (error_count / word_count) * 100.0
    return _round_metric(raw_rate, places=2)


def compute_category_metrics(
    category_counts: dict[str, int],
    word_count: int,
) -> dict[str, CategoryMetric]:
    """Compute per-category rates per 100 words and observation statuses."""
    results: dict[str, CategoryMetric] = {}
    for cat in ErrorCategory:
        count = category_counts.get(cat.value, 0)
        rate = calculate_error_rate(count, word_count)
        observed = count > 0
        status_label = "observed" if observed else "not observed in this sample"
        results[cat.value] = CategoryMetric(
            category_code=cat.value,
            count=count,
            rate_per_100_words=rate,
            observed=observed,
            status_label=status_label,
        )
    return results


def calculate_absolute_reduction(pre_rate: float, post_rate: float) -> float:
    """Absolute error-rate reduction = pre_rate - post_rate.

    Positive value indicates improvement (reduction in errors per 100 words).
    """
    return _round_metric(pre_rate - post_rate, places=2)


def calculate_relative_reduction(
    pre_rate: float,
    post_rate: float,
) -> tuple[float | None, str]:
    """Relative reduction (%) = ((pre_rate - post_rate) / pre_rate) * 100.

    SRS Section 7 Rule:
    Only calculated when pre_rate > 0.
    If pre_rate == 0, relative reduction is undefined and returns (None, 'undefined_zero_baseline').
    """
    if pre_rate <= 0.0:
        return None, "undefined_zero_baseline"
    rel_pct = ((pre_rate - post_rate) / pre_rate) * 100.0
    return _round_metric(rel_pct, places=2), "defined"


def compare_assessments(
    pre_metrics: AssessmentMetricsResult,
    post_metrics: AssessmentMetricsResult,
) -> ComparativeMetricsResult:
    """Compare baseline (pre-test) with post-test according to research rules."""
    abs_red = calculate_absolute_reduction(
        pre_metrics.overall_error_rate_per_100,
        post_metrics.overall_error_rate_per_100,
    )
    rel_red, rel_status = calculate_relative_reduction(
        pre_metrics.overall_error_rate_per_100,
        post_metrics.overall_error_rate_per_100,
    )

    category_pairs: dict[str, tuple[CategoryMetric, CategoryMetric]] = {}
    for cat in ErrorCategory:
        pre_cat = pre_metrics.category_breakdown[cat.value]
        post_cat = post_metrics.category_breakdown[cat.value]
        category_pairs[cat.value] = (pre_cat, post_cat)

    disclaimer = (
        "Descriptive change observed in speech samples. Absence of an error structure in a "
        "sample does not prove permanent acquisition or causal impact."
    )

    return ComparativeMetricsResult(
        pre_word_count=pre_metrics.word_count,
        post_word_count=post_metrics.word_count,
        pre_error_count=pre_metrics.error_count,
        post_error_count=post_metrics.error_count,
        pre_rate_per_100=pre_metrics.overall_error_rate_per_100,
        post_rate_per_100=post_metrics.overall_error_rate_per_100,
        absolute_reduction=abs_red,
        relative_reduction_pct=rel_red,
        relative_reduction_status=rel_status,
        category_comparisons=category_pairs,
        scientific_disclaimer=disclaimer,
    )


# --- Phase P12: Post-Test Comparative Metrics Engine & Reproducibility Panel ---

STANDARD_CAUTION_TEXT = (
    "This is a descriptive comparison and does not by itself show that AI caused the change."
)

CATEGORY_NAMES: dict[str, str] = {
    "TNS": "Tense and Aspect",
    "SVA": "Subject-Verb Agreement",
    "WO": "Word Order",
    "AUX": "Auxiliary Verb Usage",
    "ART": "Articles (Definite / Indefinite / Zero)",
    "PREP": "Prepositions",
    "PRO": "Pronouns",
    "OTH": "Other Syntactic Variations",
}

EXCLUDED_DECISION_TYPES = {
    "rejected",
    "uncertain",
    "transcription_related",
    "acceptable_variation",
}

EXCLUDED_FLAGS = {
    "uncertain",
    "transcription_related",
    "acceptable_variation",
}


def filter_assessable_annotations(
    annotations: Sequence[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    """Filter effective annotations for research assessability.
    
    Excludes items with decision or flag of:
    - rejected
    - uncertain
    - transcription_related
    - acceptable_variation
    Returns (assessable_annotations, excluded_count).
    """
    assessable: list[dict[str, Any]] = []
    excluded_count = 0

    for ann in annotations:
        rev_status = str(ann.get("review_status") or "").lower()
        flag = str(ann.get("flag") or "").lower()
        is_active = ann.get("is_active_for_metrics", True)

        if not is_active or rev_status in EXCLUDED_DECISION_TYPES or flag in EXCLUDED_FLAGS:
            excluded_count += 1
        else:
            assessable.append(ann)

    return assessable, excluded_count


def apply_sentence_counting_rule(
    assessable_annotations: Sequence[dict[str, Any]],
    transcript: str | None,
    counting_rule: str = "count_all",
) -> list[dict[str, Any]]:
    """Apply frozen rubric rule for multiple errors in one sentence.
    
    - 'count_all' (default): Every assessable error in a sentence is counted.
    - 'count_one_per_sentence': At most one error per sentence boundary is counted.
    """
    if counting_rule != "count_one_per_sentence" or not transcript or not transcript.strip():
        return list(assessable_annotations)

    # Split transcript into sentence spans
    sentence_spans: list[tuple[int, int]] = []
    for m in re.finditer(r'[^.!?]+(?:[.!?]+|\Z)', transcript):
        sentence_spans.append((m.start(), m.end()))

    if not sentence_spans:
        return list(assessable_annotations)

    counted: list[dict[str, Any]] = []
    seen_sentence_indices: set[int] = set()

    for ann in assessable_annotations:
        start_char = ann.get("start_char", 0)
        # Find matching sentence
        sent_idx = 0
        for idx, (s_start, s_end) in enumerate(sentence_spans):
            if s_start <= start_char < s_end:
                sent_idx = idx
                break

        if sent_idx not in seen_sentence_indices:
            seen_sentence_indices.add(sent_idx)
            counted.append(ann)

    return counted


def compute_comparative_report(
    pre_annotations: Sequence[dict[str, Any]],
    pre_word_count: int,
    post_annotations: Sequence[dict[str, Any]],
    post_word_count: int,
    rubric_version: str,
    pre_prompt_version: str | None = None,
    post_prompt_version: str | None = None,
    model_version: str = "mock-syntax-v1",
    stt_version: str = "mock-stt-v1",
    pre_transcript: str | None = None,
    post_transcript: str | None = None,
    counting_rule: str = "count_all",
    is_pre_verified: bool = False,
    is_post_verified: bool = False,
) -> dict[str, Any]:
    """Compute comprehensive Phase P12 Pre-to-Post Comparative Report.
    
    CRITICAL RESEARCH PROTOCOLS (SRS Section 7, 14, FR-15):
    1. Pure module calculation: zero I/O, deterministic output.
    2. Effective annotation set: reviewer decisions override AI candidates.
    3. Exclusions: rejected, uncertain, transcription_related, acceptable_variation excluded.
    4. Sentence counting: adheres to frozen rubric rule ('count_all' vs 'count_one_per_sentence').
    5. Relative reduction: ((pre_rate - post_rate) / pre_rate) * 100 ONLY if pre_rate > 0; otherwise N/A.
    6. Categories with zero post count: strictly labelled 'not observed in this sample', NEVER 'mastered'.
    7. Provisional marking: unreviewed assessments are visibly flagged as 'provisional'.
    8. Standard caution: 'This is a descriptive comparison and does not by itself show that AI caused the change.'
    9. Reproducibility panel: full formula, inputs, denominators, versions for auditability.
    """
    # 1. Filter assessable annotations
    pre_assessable_raw, pre_excluded = filter_assessable_annotations(pre_annotations)
    post_assessable_raw, post_excluded = filter_assessable_annotations(post_annotations)

    # 2. Apply sentence counting rule
    pre_final = apply_sentence_counting_rule(pre_assessable_raw, pre_transcript, counting_rule)
    post_final = apply_sentence_counting_rule(post_assessable_raw, post_transcript, counting_rule)

    pre_error_count = len(pre_final)
    post_error_count = len(post_final)

    # 3. Overall error rates per 100 words
    pre_rate = calculate_error_rate(pre_error_count, pre_word_count)
    post_rate = calculate_error_rate(post_error_count, post_word_count)

    # 4. Overall absolute and relative reductions
    abs_reduction = calculate_absolute_reduction(pre_rate, post_rate)
    rel_reduction, rel_status = calculate_relative_reduction(pre_rate, post_rate)

    # 5. Category-level breakdowns
    pre_cat_counts: dict[str, int] = {c.value: 0 for c in ErrorCategory}
    for ann in pre_final:
        cat = ann.get("category_code", "OTH")
        if cat in pre_cat_counts:
            pre_cat_counts[cat] += 1
        else:
            pre_cat_counts["OTH"] += 1

    post_cat_counts: dict[str, int] = {c.value: 0 for c in ErrorCategory}
    for ann in post_final:
        cat = ann.get("category_code", "OTH")
        if cat in post_cat_counts:
            post_cat_counts[cat] += 1
        else:
            post_cat_counts["OTH"] += 1

    category_comparisons: dict[str, dict[str, Any]] = {}
    syntax_fingerprint: list[dict[str, Any]] = []

    for cat in ErrorCategory:
        c_code = cat.value
        c_name = CATEGORY_NAMES.get(c_code, c_code)
        c_pre_cnt = pre_cat_counts[c_code]
        c_post_cnt = post_cat_counts[c_code]

        c_pre_rate = calculate_error_rate(c_pre_cnt, pre_word_count)
        c_post_rate = calculate_error_rate(c_post_cnt, post_word_count)

        c_abs_red = calculate_absolute_reduction(c_pre_rate, c_post_rate)
        c_rel_red, c_rel_status = calculate_relative_reduction(c_pre_rate, c_post_rate)

        c_pre_status = "observed" if c_pre_cnt > 0 else "not observed in this sample"
        # Scientific Rule: Zero count at post-test is labelled 'not observed in this sample', NEVER 'mastered'
        c_post_status = "observed" if c_post_cnt > 0 else "not observed in this sample"

        cat_data = {
            "category_code": c_code,
            "category_name": c_name,
            "pre_count": c_pre_cnt,
            "post_count": c_post_cnt,
            "pre_words": pre_word_count,
            "post_words": post_word_count,
            "pre_rate_per_100": c_pre_rate,
            "post_rate_per_100": c_post_rate,
            "absolute_reduction": c_abs_red,
            "relative_reduction_pct": c_rel_red,
            "relative_reduction_status": c_rel_status,
            "pre_status_label": c_pre_status,
            "post_status_label": c_post_status,
        }
        category_comparisons[c_code] = cat_data

        syntax_fingerprint.append({
            "category_code": c_code,
            "category_name": c_name,
            "pre_rate": c_pre_rate,
            "post_rate": c_post_rate,
            "pre_count": c_pre_cnt,
            "post_count": c_post_cnt,
            "pre_observed": c_pre_cnt > 0,
            "post_observed": c_post_cnt > 0,
            "pre_status_label": c_pre_status,
            "post_status_label": c_post_status,
        })

    # 6. Provisional status determination
    is_provisional = not (is_pre_verified and is_post_verified)
    status_label = "provisional" if is_provisional else "verified"
    provisional_warning = (
        "Provisional analysis: human review pending. One or both assessments have not been verified by a researcher."
        if is_provisional
        else None
    )

    # 7. Reproducibility Panel Metadata (Signature Feature E)
    reproducibility_panel = {
        "formulas": {
            "error_rate_per_100_words": "(assessable_error_count / total_words) * 100",
            "absolute_reduction": "pre_rate - post_rate",
            "relative_reduction_pct": "((pre_rate - post_rate) / pre_rate) * 100 (defined ONLY if pre_rate > 0)",
            "category_error_rate": "(category_assessable_count / total_words) * 100",
        },
        "pre_inputs": {
            "annotation_set_used": "effective",
            "raw_annotation_count": len(pre_annotations),
            "assessable_error_count": pre_error_count,
            "excluded_items_count": pre_excluded,
            "total_words": pre_word_count,
            "counting_rule": counting_rule,
            "rubric_version": rubric_version,
            "prompt_version": pre_prompt_version,
            "model_version": model_version,
            "stt_version": stt_version,
            "is_verified": is_pre_verified,
        },
        "post_inputs": {
            "annotation_set_used": "effective",
            "raw_annotation_count": len(post_annotations),
            "assessable_error_count": post_error_count,
            "excluded_items_count": post_excluded,
            "total_words": post_word_count,
            "counting_rule": counting_rule,
            "rubric_version": rubric_version,
            "prompt_version": post_prompt_version,
            "model_version": model_version,
            "stt_version": stt_version,
            "is_verified": is_post_verified,
        },
        "verification_status": {
            "is_pre_verified": is_pre_verified,
            "is_post_verified": is_post_verified,
            "overall_status": status_label,
        },
    }

    return {
        "is_provisional": is_provisional,
        "status_label": status_label,
        "provisional_warning": provisional_warning,
        "standard_caution": STANDARD_CAUTION_TEXT,
        "overall_comparison": {
            "pre_word_count": pre_word_count,
            "post_word_count": post_word_count,
            "pre_error_count": pre_error_count,
            "post_error_count": post_error_count,
            "pre_rate_per_100": pre_rate,
            "post_rate_per_100": post_rate,
            "absolute_reduction": abs_reduction,
            "relative_reduction_pct": rel_reduction,
            "relative_reduction_status": rel_status,
        },
        "pre_summary": {
            "word_count": pre_word_count,
            "raw_annotation_count": len(pre_annotations),
            "assessable_error_count": pre_error_count,
            "excluded_count": pre_excluded,
            "error_rate_per_100": pre_rate,
            "is_verified": is_pre_verified,
            "status_label": "verified" if is_pre_verified else "provisional",
        },
        "post_summary": {
            "word_count": post_word_count,
            "raw_annotation_count": len(post_annotations),
            "assessable_error_count": post_error_count,
            "excluded_count": post_excluded,
            "error_rate_per_100": post_rate,
            "is_verified": is_post_verified,
            "status_label": "verified" if is_post_verified else "provisional",
        },
        "category_comparisons": category_comparisons,
        "syntax_fingerprint": syntax_fingerprint,
        "reproducibility_panel": reproducibility_panel,
    }


def calculate_cohens_kappa(
    rater1_labels: Sequence[str],
    rater2_labels: Sequence[str],
    categories: Sequence[str] | None = None,
) -> AgreementMetrics:
    """Calculate Cohen's Kappa for inter-reviewer agreement (FR-10, Reviewer Cockpit)."""
    if len(rater1_labels) != len(rater2_labels):
        raise ValueError("Rater labels must have identical length.")

    n = len(rater1_labels)
    if n == 0:
        return AgreementMetrics(
            total_items=0,
            concordant_items=0,
            percent_agreement=0.0,
            cohens_kappa=None,
            interpretation="Insufficient data",
        )

    concordant = sum(1 for a, b in zip(rater1_labels, rater2_labels, strict=True) if a == b)
    po = concordant / n

    if categories is None:
        cat_set: set[str] = set(rater1_labels) | set(rater2_labels)
        all_cats = sorted(cat_set)
    else:
        all_cats = list(categories)

    # Expected agreement pe
    pe = 0.0
    for cat in all_cats:
        c1 = sum(1 for x in rater1_labels if x == cat)
        c2 = sum(1 for x in rater2_labels if x == cat)
        pe += (c1 / n) * (c2 / n)

    if pe >= 1.0:
        kappa: float | None = 1.0
    elif (1.0 - pe) == 0.0:
        kappa = None
    else:
        raw_kappa = (po - pe) / (1.0 - pe)
        kappa = _round_metric(raw_kappa, places=3)

    # Landis & Koch interpretation
    if kappa is None:
        interp = "Undefined"
    elif kappa >= 0.81:
        interp = "Almost Perfect Agreement"
    elif kappa >= 0.61:
        interp = "Substantial Agreement"
    elif kappa >= 0.41:
        interp = "Moderate Agreement"
    elif kappa >= 0.21:
        interp = "Fair Agreement"
    elif kappa >= 0.0:
        interp = "Slight Agreement"
    else:
        interp = "Poor Agreement"

    return AgreementMetrics(
        total_items=n,
        concordant_items=concordant,
        percent_agreement=_round_metric(po * 100.0, places=2),
        cohens_kappa=kappa,
        interpretation=interp,
    )


def calculate_word_error_rate(reference: str, hypothesis: str) -> float:
    """Calculate Word Error Rate (WER) using Levenshtein distance on words.

    Formula: (Substitutions + Deletions + Insertions) / len(reference_words)
    """
    ref_words = re.findall(r"\b[\w'-]+\b", reference.lower())
    hyp_words = re.findall(r"\b[\w'-]+\b", hypothesis.lower())

    r_len = len(ref_words)
    h_len = len(hyp_words)

    if r_len == 0:
        return 0.0 if h_len == 0 else 1.0

    # Dynamic programming matrix
    d = [[0] * (h_len + 1) for _ in range(r_len + 1)]
    for i in range(r_len + 1):
        d[i][0] = i
    for j in range(h_len + 1):
        d[0][j] = j

    for i in range(1, r_len + 1):
        for j in range(1, h_len + 1):
            if ref_words[i - 1] == hyp_words[j - 1]:
                d[i][j] = d[i - 1][j - 1]
            else:
                substitution = d[i - 1][j - 1] + 1
                insertion = d[i][j - 1] + 1
                deletion = d[i - 1][j] + 1
                d[i][j] = min(substitution, insertion, deletion)

    wer = d[r_len][h_len] / r_len
    return _round_metric(wer, places=4)


def evaluate_error_classification(
    gold_annotations: Sequence[tuple[str, int, int]],  # (category, start_char, end_char)
    candidate_annotations: Sequence[tuple[str, int, int]],
) -> PilotAccuracyMetrics:
    """Evaluate candidate syntactic error predictions against gold set."""
    gold_set = set(gold_annotations)
    cand_set = set(candidate_annotations)

    tp = len(gold_set & cand_set)
    fp = len(cand_set - gold_set)
    fn = len(gold_set - cand_set)

    precision = (tp / (tp + fp)) if (tp + fp) > 0 else 0.0
    recall = (tp / (tp + fn)) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    return PilotAccuracyMetrics(
        wer=0.0,
        precision=_round_metric(precision, places=4),
        recall=_round_metric(recall, places=4),
        f1_score=_round_metric(f1, places=4),
        tp=tp,
        fp=fp,
        fn=fn,
    )


# --- Phase P11: Recurrence, Active Timing & Adherence Pure Calculations (SRS FR-14) ---

def normalize_utterance_for_fingerprint(text: str) -> str:
    """Normalize learner utterance for canonical fingerprinting (FR-14).
    
    Rules:
    - Lowercase
    - Strip leading/trailing quotes and punctuation
    - Normalize internal whitespace
    - Punctuation-agnostic word token sequence
    """
    clean = text.lower().strip()
    # Strip non-alphanumeric except spaces and apostrophes inside words
    clean = re.sub(r"[^\w\s']", " ", clean)
    words = clean.split()
    return " ".join(words)


def compute_utterance_fingerprint(text: str) -> str:
    """Deterministic 32-character SHA-256 fingerprint of normalized utterance."""
    norm = normalize_utterance_for_fingerprint(text)
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()[:32]


def calculate_active_duration(
    turn_timestamps: Sequence[datetime],
    idle_threshold_seconds: int = 60,
) -> dict[str, int]:
    """Calculate active vs idle duration across a sequence of conversational turn timestamps.
    
    Documented Rule:
    Intervals between turns exceeding idle_threshold_seconds (60s) pause the active clock.
    Any interval dt <= threshold is credited to active_seconds.
    Any interval dt > threshold credits threshold to active_seconds and (dt - threshold) to idle_seconds.
    """
    if len(turn_timestamps) <= 1:
        return {
            "active_duration_seconds": 0,
            "idle_duration_seconds": 0,
            "total_wall_clock_seconds": 0,
            "idle_gaps_count": 0,
        }

    active_sec = 0
    idle_sec = 0
    idle_gaps = 0

    sorted_ts = sorted(turn_timestamps)
    for i in range(1, len(sorted_ts)):
        dt = int((sorted_ts[i] - sorted_ts[i - 1]).total_seconds())
        if dt < 0:
            continue
        if dt <= idle_threshold_seconds:
            active_sec += dt
        else:
            active_sec += idle_threshold_seconds
            idle_sec += (dt - idle_threshold_seconds)
            idle_gaps += 1

    return {
        "active_duration_seconds": active_sec,
        "idle_duration_seconds": idle_sec,
        "total_wall_clock_seconds": active_sec + idle_sec,
        "idle_gaps_count": idle_gaps,
    }


def calculate_independent_correction_rate(
    events: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    """Compute Independent Correction Rate per category and overall (SRS FR-14).
    
    Double-Count Prevention:
    Repeated references to the SAME utterance fingerprint are deduplicated into a single episode.
    Only unique error episodes count toward the denominator. If resolved across subsequent turns,
    the episode records its highest autonomy resolution (independent > hint_assisted).
    """
    episodes: dict[str, dict[str, Any]] = {}

    for ev in events:
        fp = ev.get("utterance_fingerprint") or compute_utterance_fingerprint(ev.get("learner_phrase", ""))
        cat = ev.get("target_category", "OTH")
        is_corr = ev.get("is_correct", False)
        att_type = ev.get("attempt_type")

        if fp not in episodes:
            episodes[fp] = {
                "category": cat,
                "resolved": False,
                "attempt_type": None,
            }

        # Track resolution of episode across turns
        if is_corr:
            if att_type == "independent":
                episodes[fp]["resolved"] = True
                episodes[fp]["attempt_type"] = "independent"
            elif att_type == "hint_assisted" and episodes[fp]["attempt_type"] != "independent":
                episodes[fp]["resolved"] = True
                episodes[fp]["attempt_type"] = "hint_assisted"

    # Group unique episodes by category
    category_episodes: dict[str, dict[str, int]] = {}
    for fp, ep in episodes.items():
        cat = ep["category"]
        if cat not in category_episodes:
            category_episodes[cat] = {
                "unique_error_episodes": 0,
                "independent_corrections": 0,
                "hint_assisted_corrections": 0,
                "unresolved": 0,
            }

        category_episodes[cat]["unique_error_episodes"] += 1
        if ep["resolved"] and ep["attempt_type"] == "independent":
            category_episodes[cat]["independent_corrections"] += 1
        elif ep["resolved"] and ep["attempt_type"] == "hint_assisted":
            category_episodes[cat]["hint_assisted_corrections"] += 1
        else:
            category_episodes[cat]["unresolved"] += 1

    # Format rates per category
    categories_result: dict[str, Any] = {}
    total_unique_episodes = 0
    total_independent = 0

    for cat, counts in category_episodes.items():
        tot = counts["unique_error_episodes"]
        indep = counts["independent_corrections"]
        total_unique_episodes += tot
        total_independent += indep

        rate = _round_metric((indep / tot * 100.0), 1) if tot > 0 else 0.0
        categories_result[cat] = {
            "unique_error_episodes": tot,
            "independent_corrections": indep,
            "hint_assisted_corrections": counts["hint_assisted_corrections"],
            "unresolved": counts["unresolved"],
            "independent_correction_rate_pct": rate,
        }

    overall_rate = (
        _round_metric((total_independent / total_unique_episodes * 100.0), 1)
        if total_unique_episodes > 0
        else 0.0
    )

    return {
        "overall_rate_pct": overall_rate,
        "total_unique_error_episodes": total_unique_episodes,
        "total_independent_corrections": total_independent,
        "category_breakdown": categories_result,
        "disclaimer": "Descriptive practice metric only. Never used as an official assessment score or proficiency certification.",
    }


def calculate_adherence_statistics(
    sessions: Sequence[dict[str, Any]],
    expected_sessions_per_week: int = 3,
    expected_minutes_per_session: int = 15,
) -> dict[str, Any]:
    """Calculate researcher intervention adherence metrics across practice sessions.
    
    Computes total active minutes, completed sessions, and adherence rate vs expected target.
    """
    total_active_seconds = sum(s.get("active_duration_seconds", 0) for s in sessions)
    completed_sessions = sum(1 for s in sessions if s.get("status") == "completed")
    total_active_minutes = _round_metric(total_active_seconds / 60.0, 1)

    # Estimate span in weeks from earliest to latest session
    weeks_count = 1.0
    valid_starts = [s["start_time"] for s in sessions if s.get("start_time")]
    if len(valid_starts) >= 2:
        earliest = min(valid_starts)
        latest = max(valid_starts)
        days = max(1, (latest - earliest).days)
        weeks_count = max(1.0, _round_metric(days / 7.0, 1))

    expected_total_minutes = weeks_count * expected_sessions_per_week * expected_minutes_per_session
    expected_total_sessions = int(weeks_count * expected_sessions_per_week)

    adherence_pct = (
        _round_metric((total_active_minutes / expected_total_minutes * 100.0), 1)
        if expected_total_minutes > 0
        else 100.0
    )

    sessions_per_week = _round_metric(completed_sessions / weeks_count, 1)

    return {
        "total_active_minutes": total_active_minutes,
        "completed_sessions": completed_sessions,
        "active_duration_seconds": total_active_seconds,
        "estimated_weeks": weeks_count,
        "sessions_per_week": sessions_per_week,
        "expected_sessions_per_week": expected_sessions_per_week,
        "expected_total_minutes": expected_total_minutes,
        "adherence_percentage": adherence_pct,
        "status_label": "High Adherence" if adherence_pct >= 80.0 else "Needs Encouragement",
    }

