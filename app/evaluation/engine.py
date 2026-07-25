"""Evaluation Engine.

Scores a completed roleplay transcript by prompting an LLM with a
dedicated evaluation prompt (see prompts/evaluation_prompts.py) — a
different system prompt, and a different model role (sales coach, not
customer persona), from the Prompt Builder (Step 14).

Unlike the Persona Engine (Step 13) and Conversation State Manager (Step
15), this is the first engine in this codebase that actually calls an
LLM — judging a full conversation's quality is exactly the kind of
holistic reasoning rule-based heuristics can't do well. It depends on
LLMService (the ABC from Step 16), never a concrete provider, so it works
unchanged regardless of whether Claude or GPT is configured.
"""

from app.prompts.evaluation_prompts import (
    render_evaluator_role,
    render_output_format,
    render_scoring_rubric,
)
from app.prompts.evaluation_prompts import render_transcript_section as render_evaluation_transcript
from app.schemas.evaluation import EvaluationRequest, EvaluationResult
from app.schemas.llm import LLMRequest
from app.services.llm import LLMService, LLMServiceError

# Low but non-zero: scoring should be consistent across runs of the same
# transcript without being fully rigid, since this is still an LLM
# judgment call, not a deterministic rule (contrast with Steps 13/15).
_EVALUATION_TEMPERATURE = 0.3
_EVALUATION_MAX_TOKENS = 1024


class EvaluationEngineError(Exception):
    """Raised when the LLM call fails or its response isn't valid, structured JSON."""


class EvaluationEngine:
    def __init__(self, llm_service: LLMService) -> None:
        self._llm_service = llm_service

    async def evaluate(self, request: EvaluationRequest) -> EvaluationResult:
        system_prompt = "\n\n".join(
            [
                render_evaluator_role(),
                render_scoring_rubric(),
                render_evaluation_transcript(request.transcript),
                render_output_format(),
            ]
        )

        llm_request = LLMRequest(
            system_prompt=system_prompt,
            messages=[],
            max_tokens=_EVALUATION_MAX_TOKENS,
            temperature=_EVALUATION_TEMPERATURE,
        )

        try:
            response = await self._llm_service.complete(llm_request)
        except LLMServiceError as error:
            raise EvaluationEngineError(f"Evaluation LLM call failed: {error}") from error

        return self._parse_response(response.content)

    @staticmethod
    def _parse_response(content: str) -> EvaluationResult:
        cleaned = _strip_code_fences(content)
        try:
            return EvaluationResult.model_validate_json(cleaned)
        except ValueError as error:
            raise EvaluationEngineError(
                f"Evaluation response was not valid structured JSON: {error}"
            ) from error


def _strip_code_fences(text: str) -> str:
    """Defensively strips a ```json ... ``` wrapper.

    render_output_format() explicitly instructs the model not to use one,
    but models don't always follow formatting instructions perfectly, and
    this costs nothing when the instruction was followed.
    """
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped

    lines = stripped.splitlines()
    lines = lines[1:]  # drop the opening fence (``` or ```json)
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()
