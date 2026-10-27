"""Tests for Mock LLM Provider.

Validates candidate error analysis, Hint Ladder level stepping, and zero-API key execution.
"""

import pytest

from app.services.llm.mock import MockLLMProvider


@pytest.mark.asyncio
async def test_mock_llm_syntax_analysis_sva():
    provider = MockLLMProvider()
    transcript = "He go to college every day."
    result = await provider.analyze_syntax(transcript, rubric_version="v1.0")

    assert len(result.candidate_errors) == 1
    err = result.candidate_errors[0]
    assert err.category_code == "SVA"
    assert err.candidate_error == "go"
    assert err.suggested_correction == "goes"
    assert "third-person singular" in err.explanation
    assert err.confidence > 0.9


@pytest.mark.asyncio
async def test_mock_llm_syntax_analysis_multiple_patterns():
    provider = MockLLMProvider()
    transcript = "Yesterday I have seen him and we discuss about the project."
    result = await provider.analyze_syntax(transcript, rubric_version="v1.0")

    # Should detect both TNS and PREP
    categories = {e.category_code for e in result.candidate_errors}
    assert "TNS" in categories
    assert "PREP" in categories


@pytest.mark.asyncio
async def test_mock_llm_hint_ladder_progression():
    provider = MockLLMProvider()

    # L0: Quote phrase
    l0 = await provider.generate_tutor_turn("SVA", "He go to college", 0, "v1.0")
    assert l0.ladder_level == 0
    assert 'He go to college' in l0.tutor_utterance

    # L1: Hint question
    l1 = await provider.generate_tutor_turn("SVA", "He go to college", 1, "v1.0")
    assert l1.ladder_level == 1
    assert l1.hint_question is not None

    # L2: Rule cue
    l2 = await provider.generate_tutor_turn("SVA", "He go to college", 2, "v1.0")
    assert l2.ladder_level == 2
    assert l2.rule_cue is not None

    # L3: Reveal answer + transfer check
    l3 = await provider.generate_tutor_turn("SVA", "He go to college", 3, "v1.0")
    assert l3.ladder_level == 3
    assert l3.revealed_answer == "He goes to college every day."
    assert l3.transfer_prompt is not None
