"""Pure Research Metrics Module for SyntaxLens.

CRITICAL RESEARCH INTEGRITY RULE:
All metrics must be computed strictly by this pure, stateless, zero-I/O module.
Formulas must never be re-implemented in the UI or duplicated across database queries.
All calculations match SRS Section 7, Section 14, and approved Signature Features.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
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
