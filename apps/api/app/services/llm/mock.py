"""Deterministic Mock LLM Provider.

RESEARCH INTEGRITY RULE:
Implements LLMProvider interface with zero external API keys.
Guarantees deterministic, reproducible candidate syntactic error analysis
and Hint Ladder tutor turns based on PhD research corpus golden sets.
"""

import json
from typing import Any

from app.services.llm.base import (
    AnnotationItem,
    AssessorOutput,
    LLMProvider,
    TutorResponse,
)

# Golden Test Fixture Transcripts for 8 Syntactic Categories
GOLDEN_FIXTURES: dict[str, list[dict[str, Any]]] = {
    # 1. Subject-Verb Agreement (SVA) - SRS Appendix A
    "He go to college every day.": [
        {
            "span_text": "go",
            "char_start": 3,
            "char_end": 5,
            "category_code": "SVA",
            "proposed_correction": "goes",
            "explanation": "In simple present tense with a third-person singular subject ('He'), the verb requires the -s/-es inflection.",
            "confidence": 0.98,
            "flag": "candidate_error",
            "time_start": 0.8,
            "time_end": 1.1,
        }
    ],
    # 2. Tense & Aspect (TNS)
    "Yesterday I have seen him at the station.": [
        {
            "span_text": "have seen",
            "char_start": 12,
            "char_end": 21,
            "category_code": "TNS",
            "proposed_correction": "saw",
            "explanation": "With a past time adverbial ('Yesterday'), the simple past tense is required rather than the present perfect.",
            "confidence": 0.96,
            "flag": "candidate_error",
            "time_start": 1.2,
            "time_end": 1.8,
        }
    ],
    # 3. Word Order (WO)
    "Always he is coming late to class.": [
        {
            "span_text": "Always he is coming",
            "char_start": 0,
            "char_end": 19,
            "category_code": "WO",
            "proposed_correction": "He is always coming",
            "explanation": "Adverbs of frequency typically follow the subject and auxiliary verb in English syntax.",
            "confidence": 0.94,
            "flag": "candidate_error",
            "time_start": 0.5,
            "time_end": 2.2,
        }
    ],
    # 4. Auxiliary Usage (AUX)
    "She can to solve this problem.": [
        {
            "span_text": "can to solve",
            "char_start": 4,
            "char_end": 16,
            "category_code": "AUX",
            "proposed_correction": "can solve",
            "explanation": "Modal auxiliary verbs like 'can' take the bare infinitive without 'to'.",
            "confidence": 0.97,
            "flag": "candidate_error",
            "time_start": 0.7,
            "time_end": 1.9,
        }
    ],
    # 5. Articles & Determiners (ART)
    "He is studying in the engineering college.": [
        {
            "span_text": "the engineering college",
            "char_start": 18,
            "char_end": 41,
            "category_code": "ART",
            "proposed_correction": "an engineering college",
            "explanation": "Non-unique singular countable noun phrases require the indefinite article 'an'.",
            "confidence": 0.93,
            "flag": "candidate_error",
            "time_start": 1.5,
            "time_end": 3.0,
        }
    ],
    # 6. Prepositions (PREP)
    "We will discuss about this topic.": [
        {
            "span_text": "discuss about",
            "char_start": 8,
            "char_end": 21,
            "category_code": "PREP",
            "proposed_correction": "discuss",
            "explanation": "The transitive verb 'discuss' takes a direct object without the preposition 'about'.",
            "confidence": 0.95,
            "flag": "candidate_error",
            "time_start": 1.0,
            "time_end": 2.1,
        }
    ],
    # 7. Pronoun Reference & Resumptive Pronouns (PRO)
    "My friend he told me about the exam.": [
        {
            "span_text": "he",
            "char_start": 10,
            "char_end": 12,
            "category_code": "PRO",
            "proposed_correction": "",
            "explanation": "Resumptive subject pronouns are non-standard when the overt noun phrase subject is present.",
            "confidence": 0.92,
            "flag": "candidate_error",
            "time_start": 1.2,
            "time_end": 1.5,
        }
    ],
    # 8. Other Syntactic Anomalies (OTH)
    "This machine is more better than old one.": [
        {
            "span_text": "more better",
            "char_start": 16,
            "char_end": 27,
            "category_code": "OTH",
            "proposed_correction": "better",
            "explanation": "Double comparative inflection is non-standard; use either -er or 'more', never both.",
            "confidence": 0.90,
            "flag": "candidate_error",
            "time_start": 1.6,
            "time_end": 2.5,
        }
    ],
    # Edge Case: Acceptable Indian English Stative Progressive
    "I am knowing this subject very well.": [
        {
            "span_text": "am knowing",
            "char_start": 2,
            "char_end": 12,
            "category_code": "TNS",
            "proposed_correction": "know",
            "explanation": "Stative progressive is an established regional variation in Indian English.",
            "confidence": 0.88,
            "flag": "acceptable_variation",
            "time_start": 0.6,
            "time_end": 1.4,
        }
    ],
    # Edge Case: Disfluency & Ambiguity
    "um... I think that, that he go": [
        {
            "span_text": "go",
            "char_start": 28,
            "char_end": 30,
            "category_code": "SVA",
            "proposed_correction": "goes",
            "explanation": "Third-person singular present tense requires verb suffix -s/-es.",
            "confidence": 0.95,
            "flag": "candidate_error",
            "time_start": 3.0,
            "time_end": 3.4,
        },
        {
            "span_text": "that, that",
            "char_start": 14,
            "char_end": 24,
            "category_code": "OTH",
            "proposed_correction": "that",
            "explanation": "Acoustic repetition/stutter without syntactic deviation.",
            "confidence": 0.65,
            "flag": "uncertain",
            "time_start": 1.5,
            "time_end": 2.2,
        },
    ],
}


class MockLLMProvider(LLMProvider):
    """Deterministic, fixture-driven Mock LLM provider for zero-API-key testing and CI."""

    def __init__(self, model_version: str = "mock-syntax-v1.0"):
        self.model_version = model_version

    async def analyze_syntax(
        self,
        transcript: str,
        rubric_version: str = "v1.0-jam-phd",
        prompt_version: str = "v1.0-assessor",
        words_json: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> AssessorOutput:
        """Deterministic syntax analysis using golden set fixtures."""
        clean_text = transcript.strip()
        annotations_raw: list[dict[str, Any]] = []

        # 1. Exact match in Golden Fixtures
        if clean_text in GOLDEN_FIXTURES:
            annotations_raw = list(GOLDEN_FIXTURES[clean_text])
        else:
            # 2. Check for multiple pattern matches across clean_text
            # SVA
            if "he go " in clean_text.lower() or "he go." in clean_text.lower() or "he go\n" in clean_text.lower():
                idx = clean_text.lower().find("he go") + 3
                annotations_raw.append({
                    "span_text": clean_text[idx:idx + 2],
                    "char_start": idx,
                    "char_end": idx + 2,
                    "category_code": "SVA",
                    "proposed_correction": "goes",
                    "explanation": "In third-person singular present tense ('he'), the verb takes the -s/-es suffix.",
                    "confidence": 0.98,
                    "flag": "candidate_error",
                })

            # TNS (have seen)
            if "have seen" in clean_text.lower():
                idx = clean_text.lower().find("have seen")
                annotations_raw.append({
                    "span_text": clean_text[idx:idx + 9],
                    "char_start": idx,
                    "char_end": idx + 9,
                    "category_code": "TNS",
                    "proposed_correction": "saw",
                    "explanation": "With a past time adverbial, the simple past tense is required rather than the present perfect.",
                    "confidence": 0.96,
                    "flag": "candidate_error",
                })

            # PREP (discuss about)
            if "discuss about" in clean_text.lower():
                idx = clean_text.lower().find("discuss about")
                annotations_raw.append({
                    "span_text": clean_text[idx:idx + 13],
                    "char_start": idx,
                    "char_end": idx + 13,
                    "category_code": "PREP",
                    "proposed_correction": "discuss",
                    "explanation": "The transitive verb 'discuss' takes direct object without preposition 'about'.",
                    "confidence": 0.95,
                    "flag": "candidate_error",
                })

            # WO (always he is coming)
            if "always he is coming" in clean_text.lower():
                idx = clean_text.lower().find("always he is coming")
                annotations_raw.append({
                    "span_text": clean_text[idx:idx + 19],
                    "char_start": idx,
                    "char_end": idx + 19,
                    "category_code": "WO",
                    "proposed_correction": "He is always coming",
                    "explanation": "Adverbs of frequency typically follow the subject and auxiliary verb.",
                    "confidence": 0.94,
                    "flag": "candidate_error",
                })

            # AUX (can to solve)
            if "can to solve" in clean_text.lower():
                idx = clean_text.lower().find("can to solve")
                annotations_raw.append({
                    "span_text": clean_text[idx:idx + 12],
                    "char_start": idx,
                    "char_end": idx + 12,
                    "category_code": "AUX",
                    "proposed_correction": "can solve",
                    "explanation": "Modal auxiliary verbs like 'can' take the bare infinitive without 'to'.",
                    "confidence": 0.97,
                    "flag": "candidate_error",
                })

            # ART (the engineering college)
            if "the engineering college" in clean_text.lower():
                idx = clean_text.lower().find("the engineering college")
                annotations_raw.append({
                    "span_text": clean_text[idx:idx + 23],
                    "char_start": idx,
                    "char_end": idx + 23,
                    "category_code": "ART",
                    "proposed_correction": "an engineering college",
                    "explanation": "Non-unique singular countable noun phrases require the indefinite article 'an'.",
                    "confidence": 0.93,
                    "flag": "candidate_error",
                })

            # PRO (friend he told)
            if "friend he told" in clean_text.lower():
                idx = clean_text.lower().find("friend he told") + 7
                annotations_raw.append({
                    "span_text": clean_text[idx:idx + 2],
                    "char_start": idx,
                    "char_end": idx + 2,
                    "category_code": "PRO",
                    "proposed_correction": "",
                    "explanation": "Resumptive subject pronouns are non-standard when the overt noun phrase subject is present.",
                    "confidence": 0.92,
                    "flag": "candidate_error",
                })

            # OTH (more better)
            if "more better" in clean_text.lower():
                idx = clean_text.lower().find("more better")
                annotations_raw.append({
                    "span_text": clean_text[idx:idx + 11],
                    "char_start": idx,
                    "char_end": idx + 11,
                    "category_code": "OTH",
                    "proposed_correction": "better",
                    "explanation": "Double comparative inflection is non-standard; use either -er or 'more', never both.",
                    "confidence": 0.90,
                    "flag": "candidate_error",
                })

            # Acceptable variation (am knowing)
            if "am knowing" in clean_text.lower():
                idx = clean_text.lower().find("am knowing")
                annotations_raw.append({
                    "span_text": clean_text[idx:idx + 10],
                    "char_start": idx,
                    "char_end": idx + 10,
                    "category_code": "TNS",
                    "proposed_correction": "know",
                    "explanation": "Stative progressive is an established regional variation in Indian English.",
                    "confidence": 0.88,
                    "flag": "acceptable_variation",
                })

        annotations = [AnnotationItem(**item) for item in annotations_raw]

        return AssessorOutput(
            annotations=annotations,
            model_notes="Deterministic mock analysis based on PhD corpus baseline.",
            model_version=self.model_version,
            rubric_version=rubric_version,
            prompt_version=prompt_version,
            raw_response=json.dumps({"annotations": [a.model_dump() for a in annotations]}),
        )

    async def generate_tutor_turn(
        self,
        target_category: str,
        learner_utterance: str,
        ladder_level: int,
        prompt_version: str,
    ) -> TutorResponse:
        """Hint Ladder turn generation without altering official scores."""
        if ladder_level == 0:
            return TutorResponse(
                tutor_utterance=f'Let\'s look at what you just said: "{learner_utterance}". How might you say that more accurately?',
                ladder_level=0,
                target_category=target_category,
            )
        elif ladder_level == 1:
            return TutorResponse(
                tutor_utterance="Notice the subject and the verb in your sentence. When the subject is third-person singular (he/she/it), what ending does the verb usually take in the present tense?",
                ladder_level=1,
                target_category=target_category,
                hint_question="What ending is added to simple present verbs with he/she/it?",
            )
        elif ladder_level == 2:
            return TutorResponse(
                tutor_utterance="Rule cue: In English subject-verb agreement, third-person singular subjects (he, she, it) require the verb to end with '-s' or '-es' (e.g., 'he goes'). Try saying the sentence again with this rule.",
                ladder_level=2,
                target_category=target_category,
                rule_cue="Add -s or -es to the verb base.",
            )
        else:
            return TutorResponse(
                tutor_utterance='The natural form is: "He goes to college every day." Now, let\'s test your transfer: can you tell me what your friend does every morning?',
                ladder_level=3,
                target_category=target_category,
                revealed_answer="He goes to college every day.",
                transfer_prompt="What does your friend do every morning?",
            )
