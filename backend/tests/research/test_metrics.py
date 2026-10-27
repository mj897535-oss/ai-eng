"""Unit tests for the Pure Research Metrics Module.

Proves mathematical fidelity with SRS Section 7, Section 14, and Signature Features.
Zero I/O, zero network, 100% deterministic.
"""

import pytest

from app.research.metrics import (
    AssessmentMetricsResult,
    ErrorCategory,
    calculate_absolute_reduction,
    calculate_cohens_kappa,
    calculate_error_rate,
    calculate_relative_reduction,
    calculate_word_error_rate,
    compare_assessments,
    compute_category_metrics,
    count_words,
    evaluate_error_classification,
)


class TestWordCounting:
    """Test transcript tokenization and word counting."""

    def test_empty_and_whitespace(self) -> None:
        assert count_words("") == 0
        assert count_words("   \n\t  ") == 0

    def test_standard_transcription(self) -> None:
        # Example from SRS Appendix A: "He go to college every day."
        text = "He go to college every day."
        assert count_words(text) == 6

    def test_hyphenated_and_apostrophes(self) -> None:
        text = "Well, it's a well-known fact that they didn't arrive."
        # words: Well, it's, a, well-known, fact, that, they, didn't, arrive = 9
        assert count_words(text) == 9

    def test_punctuation_stripping(self) -> None:
        text = "Hello... world! Are you there?? Yes, I am."
        assert count_words(text) == 8


class TestErrorRateCalculations:
    """Test rate per 100 words and zero protections."""

    def test_zero_words(self) -> None:
        assert calculate_error_rate(error_count=5, word_count=0) == 0.0

    def test_standard_rate(self) -> None:
        # 5 errors in 100 words = 5.0
        assert calculate_error_rate(error_count=5, word_count=100) == 5.0
        # 6 errors in 150 words = (6 / 150) * 100 = 4.0
        assert calculate_error_rate(error_count=6, word_count=150) == 4.0

    def test_rounding_precision(self) -> None:
        # 1 error in 30 words = 3.3333... -> 3.33
        assert calculate_error_rate(error_count=1, word_count=30) == 3.33


class TestCategoryObservationFlags:
    """Test SRS Section 7 & Signature Feature B: 'not observed in this sample'."""

    def test_all_eight_categories_present(self) -> None:
        counts = {"SVA": 2, "TNS": 1}
        metrics = compute_category_metrics(counts, word_count=100)

        # Must contain all 8 categories
        assert len(metrics) == 8
        for cat in ErrorCategory:
            assert cat.value in metrics

        # SVA observed
        sva = metrics["SVA"]
        assert sva.count == 2
        assert sva.rate_per_100_words == 2.0
        assert sva.observed is True
        assert sva.status_label == "observed"

        # ART unobserved
        art = metrics["ART"]
        assert art.count == 0
        assert art.rate_per_100_words == 0.0
        assert art.observed is False
        assert art.status_label == "not observed in this sample"


class TestReductionsAndZeroBaseline:
    """Test Absolute and Relative Reductions per SRS Section 7."""

    def test_absolute_reduction(self) -> None:
        # Pre rate 8.50, Post rate 3.25 -> reduction of 5.25
        assert calculate_absolute_reduction(8.50, 3.25) == 5.25
        # Post rate higher (regression)
        assert calculate_absolute_reduction(4.00, 6.00) == -2.00

    def test_relative_reduction_standard(self) -> None:
        # Pre rate 10.0, Post rate 4.0 -> (10 - 4)/10 * 100 = 60.0%
        val, status = calculate_relative_reduction(10.0, 4.0)
        assert val == 60.0
        assert status == "defined"

    def test_relative_reduction_zero_baseline_rule(self) -> None:
        """CRITICAL: SRS Section 7 mandates:

        'If the pre-test rate is zero, relative reduction is undefined and
        should be shown as N/A.'
        """
        val, status = calculate_relative_reduction(0.0, 2.0)
        assert val is None
        assert status == "undefined_zero_baseline"


class TestComparativeIntegration:
    """Test overall pre/post comparison reporting."""

    def test_compare_assessments(self) -> None:
        pre = AssessmentMetricsResult(
            word_count=100,
            error_count=8,
            overall_error_rate_per_100=8.0,
            category_breakdown=compute_category_metrics({"TNS": 4, "SVA": 4}, 100),
            rubric_version="v1.0",
            model_version="mock-v1",
            stt_version="mock-v1",
        )
        post = AssessmentMetricsResult(
            word_count=120,
            error_count=3,
            overall_error_rate_per_100=2.5,
            category_breakdown=compute_category_metrics({"TNS": 1, "SVA": 2}, 120),
            rubric_version="v1.0",
            model_version="mock-v1",
            stt_version="mock-v1",
        )

        comparison = compare_assessments(pre, post)
        assert comparison.pre_rate_per_100 == 8.0
        assert comparison.post_rate_per_100 == 2.5
        assert comparison.absolute_reduction == 5.5
        assert comparison.relative_reduction_pct == 68.75
        assert comparison.relative_reduction_status == "defined"
        assert "Descriptive change" in comparison.scientific_disclaimer


class TestReviewerAgreement:
    """Test Cohen's Kappa for Reviewer Cockpit (Signature Feature D)."""

    def test_perfect_agreement(self) -> None:
        r1 = ["ACCEPTED", "REJECTED", "ACCEPTED", "EDITED"]
        r2 = ["ACCEPTED", "REJECTED", "ACCEPTED", "EDITED"]
        res = calculate_cohens_kappa(r1, r2)
        assert res.concordant_items == 4
        assert res.percent_agreement == 100.0
        assert res.cohens_kappa == 1.0
        assert res.interpretation == "Almost Perfect Agreement"

    def test_empty_lists(self) -> None:
        res = calculate_cohens_kappa([], [])
        assert res.total_items == 0
        assert res.cohens_kappa is None

    def test_mismatched_lengths_raise(self) -> None:
        with pytest.raises(ValueError):
            calculate_cohens_kappa(["A"], ["A", "B"])


class TestPilotKitMetrics:
    """Test WER and Error Classification Precision/Recall (Signature Feature F)."""

    def test_word_error_rate_exact_match(self) -> None:
        text = "The participant completed the assessment on time."
        assert calculate_word_error_rate(text, text) == 0.0

    def test_word_error_rate_substitution_and_insertion(self) -> None:
        ref = "He go to college"
        hyp = "He goes to the college"
        # ref = 4 words; hyp has substitution ('go' -> 'goes') and insertion ('the') = 2 edits / 4 = 0.50
        assert calculate_word_error_rate(ref, hyp) == 0.50

    def test_evaluate_error_classification(self) -> None:
        # Spans: (category, start_char, end_char)
        gold = [("SVA", 3, 5), ("TNS", 10, 15)]
        pred = [("SVA", 3, 5), ("ART", 20, 23)]  # 1 TP, 1 FP, 1 FN

        eval_res = evaluate_error_classification(gold, pred)
        assert eval_res.tp == 1
        assert eval_res.fp == 1
        assert eval_res.fn == 1
        assert eval_res.precision == 0.5
        assert eval_res.recall == 0.5
        assert eval_res.f1_score == 0.5
