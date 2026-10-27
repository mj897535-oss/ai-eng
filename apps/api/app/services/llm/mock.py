"""Deterministic Mock LLM Provider.

Provides faithful candidate error analysis and Hint Ladder tutor turns
without requiring external API keys.
"""


from app.services.llm.base import (
    AnalysisResult,
    CandidateError,
    LLMProvider,
    TutorResponse,
)


class MockLLMProvider(LLMProvider):
    def __init__(self) -> None:
        self.model_version = "mock-syntax-v1.0"

    async def analyze_syntax(
        self,
        transcript: str,
        rubric_version: str,
    ) -> AnalysisResult:
        errors: list[CandidateError] = []

        # Deterministic detection patterns based on PhD research corpus
        # Case 1: "He go" -> SVA
        if "He go " in transcript or "he go " in transcript:
            start = transcript.lower().find("he go ") + 3
            errors.append(
                CandidateError(
                    candidate_error="go",
                    suggested_correction="goes",
                    category_code="SVA",
                    explanation="In third-person singular present tense ('he'), the verb takes the -s/-es suffix.",
                    confidence=0.96,
                    start_char=start,
                    end_char=start + 2,
                    start_time_ms=500,
                    end_time_ms=800,
                )
            )

        # Case 2: "yesterday he go" or "I have seen him yesterday" -> TNS
        if "yesterday" in transcript.lower() and "have seen" in transcript.lower():
            start = transcript.lower().find("have seen")
            errors.append(
                CandidateError(
                    candidate_error="have seen",
                    suggested_correction="saw",
                    category_code="TNS",
                    explanation="With a past time adverbial ('yesterday'), the simple past tense is required rather than the present perfect.",
                    confidence=0.94,
                    start_char=start,
                    end_char=start + 9,
                    start_time_ms=1200,
                    end_time_ms=1800,
                )
            )

        # Case 3: "discuss about" -> PREP
        if "discuss about" in transcript.lower():
            start = transcript.lower().find("discuss about")
            errors.append(
                CandidateError(
                    candidate_error="discuss about",
                    suggested_correction="discuss",
                    category_code="PREP",
                    explanation="The transitive verb 'discuss' takes a direct object without the preposition 'about'.",
                    confidence=0.91,
                    start_char=start,
                    end_char=start + 13,
                    start_time_ms=2000,
                    end_time_ms=2800,
                )
            )

        return AnalysisResult(
            candidate_errors=errors,
            model_version=self.model_version,
            rubric_version=rubric_version,
            raw_response='{"status": "analyzed", "findings_count": ' + str(len(errors)) + "}",
        )

    async def generate_tutor_turn(
        self,
        target_category: str,
        learner_utterance: str,
        ladder_level: int,
        prompt_version: str,
    ) -> TutorResponse:
        # Hint Ladder: L0 quote, L1 hint question, L2 rule cue, L3 reveal
        if ladder_level == 0:
            return TutorResponse(
                tutor_utterance=f'Let\'s look at what you just said: "{learner_utterance}". How might you say that more accurately?',
                ladder_level=0,
                target_category=target_category,
                hint_question=None,
                rule_cue=None,
                revealed_answer=None,
                transfer_prompt=None,
            )
        elif ladder_level == 1:
            return TutorResponse(
                tutor_utterance='Notice the subject and the verb in your sentence. When the subject is third-person singular (he/she/it), what ending does the verb usually take in the present tense?',
                ladder_level=1,
                target_category=target_category,
                hint_question="What ending is added to simple present verbs with he/she/it?",
                rule_cue=None,
                revealed_answer=None,
                transfer_prompt=None,
            )
        elif ladder_level == 2:
            return TutorResponse(
                tutor_utterance="Rule cue: In English subject-verb agreement, third-person singular subjects (he, she, it) require the verb to end with '-s' or '-es' (e.g., 'he goes'). Try saying the sentence again with this rule.",
                ladder_level=2,
                target_category=target_category,
                hint_question=None,
                rule_cue="Add -s or -es to the verb base.",
                revealed_answer=None,
                transfer_prompt=None,
            )
        else:  # ladder_level == 3 (Reveal + transfer check)
            return TutorResponse(
                tutor_utterance='The natural form is: "He goes to college every day." Now, let\'s test your transfer: can you tell me what your friend does every morning?',
                ladder_level=3,
                target_category=target_category,
                hint_question=None,
                rule_cue=None,
                revealed_answer="He goes to college every day.",
                transfer_prompt="What does your friend do every morning?",
            )
