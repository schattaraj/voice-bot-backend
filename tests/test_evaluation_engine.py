"""Tests for the Evaluation Engine: prompt content, structured-JSON
parsing (including markdown code-fence robustness), error wrapping, and
FastAPI dependency composition."""

import json

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.core.dependencies import get_evaluation_engine, get_llm_service
from app.evaluation.engine import EvaluationEngine, EvaluationEngineError
from app.schemas.evaluation import EvaluationRequest, EvaluationResult
from app.schemas.llm import LLMRequest, LLMResponse, LLMUsage
from app.schemas.transcript import TranscriptTurn
from app.services.llm import LLMService, LLMServiceError

VALID_RESULT_JSON = json.dumps(
    {
        "overall_score": 78,
        "discovery_score": 65,
        "objection_handling_score": 80,
        "communication_score": 85,
        "closing_score": 70,
        "strengths": ["Built rapport quickly"],
        "weaknesses": ["Rushed past discovery"],
        "recommendations": ["Ask more open-ended questions early"],
    }
)

TRANSCRIPT = [
    TranscriptTurn(speaker="ai-buyer", text="Hello, this is Alicia.", timestamp_ms=0),
    TranscriptTurn(speaker="rep", text="Thanks for taking the call.", timestamp_ms=3200),
]


class _FakeLLMService(LLMService):
    def __init__(self, content: str) -> None:
        self._content = content
        self.last_request: LLMRequest | None = None

    @property
    def provider_name(self) -> str:
        return "fake"

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.last_request = request
        return LLMResponse(
            content=self._content,
            provider="fake",
            model="fake-model",
            usage=LLMUsage(input_tokens=10, output_tokens=10),
        )


class _RaisingLLMService(LLMService):
    @property
    def provider_name(self) -> str:
        return "fake"

    async def complete(self, request: LLMRequest) -> LLMResponse:
        raise LLMServiceError("upstream is down")


async def test_evaluate_parses_well_formed_json_response():
    engine = EvaluationEngine(llm_service=_FakeLLMService(VALID_RESULT_JSON))

    result = await engine.evaluate(EvaluationRequest(transcript=TRANSCRIPT))

    assert isinstance(result, EvaluationResult)
    assert result.overall_score == 78
    assert result.discovery_score == 65
    assert result.objection_handling_score == 80
    assert result.communication_score == 85
    assert result.closing_score == 70
    assert result.strengths == ["Built rapport quickly"]
    assert result.weaknesses == ["Rushed past discovery"]
    assert result.recommendations == ["Ask more open-ended questions early"]


async def test_evaluate_strips_markdown_code_fences():
    fenced = f"```json\n{VALID_RESULT_JSON}\n```"
    engine = EvaluationEngine(llm_service=_FakeLLMService(fenced))

    result = await engine.evaluate(EvaluationRequest(transcript=TRANSCRIPT))

    assert result.overall_score == 78


async def test_evaluate_sends_transcript_and_rubric_in_the_system_prompt():
    fake_llm = _FakeLLMService(VALID_RESULT_JSON)
    engine = EvaluationEngine(llm_service=fake_llm)

    await engine.evaluate(EvaluationRequest(transcript=TRANSCRIPT))

    sent_prompt = fake_llm.last_request.system_prompt
    assert "sales coach" in sent_prompt.lower()
    assert "discovery_score" in sent_prompt
    assert "Hello, this is Alicia." in sent_prompt
    assert "Thanks for taking the call." in sent_prompt
    assert "ONLY a single JSON object" in sent_prompt


async def test_evaluate_handles_empty_transcript_without_crashing():
    fake_llm = _FakeLLMService(VALID_RESULT_JSON)
    engine = EvaluationEngine(llm_service=fake_llm)

    await engine.evaluate(EvaluationRequest(transcript=[]))

    assert "empty transcript" in fake_llm.last_request.system_prompt


async def test_evaluate_raises_on_malformed_json():
    engine = EvaluationEngine(llm_service=_FakeLLMService("not json at all"))

    try:
        await engine.evaluate(EvaluationRequest(transcript=TRANSCRIPT))
        assert False, "expected EvaluationEngineError"
    except EvaluationEngineError:
        pass


async def test_evaluate_raises_when_json_is_missing_required_fields():
    incomplete = json.dumps({"overall_score": 50})
    engine = EvaluationEngine(llm_service=_FakeLLMService(incomplete))

    try:
        await engine.evaluate(EvaluationRequest(transcript=TRANSCRIPT))
        assert False, "expected EvaluationEngineError"
    except EvaluationEngineError:
        pass


async def test_evaluate_wraps_llm_service_errors():
    engine = EvaluationEngine(llm_service=_RaisingLLMService())

    try:
        await engine.evaluate(EvaluationRequest(transcript=TRANSCRIPT))
        assert False, "expected EvaluationEngineError"
    except EvaluationEngineError:
        pass


def test_dependency_composition_uses_the_overridden_llm_service():
    """Proves get_evaluation_engine() actually composes with
    get_llm_service() through FastAPI's DI graph: overriding the LLM
    dependency changes what the evaluation route uses, with no other
    wiring."""

    test_app = FastAPI()

    @test_app.post("/evaluate")
    async def evaluate_route(engine: EvaluationEngine = Depends(get_evaluation_engine)):
        result = await engine.evaluate(EvaluationRequest(transcript=TRANSCRIPT))
        return result.model_dump()

    test_app.dependency_overrides[get_llm_service] = lambda: _FakeLLMService(VALID_RESULT_JSON)
    client = TestClient(test_app)

    response = client.post("/evaluate").json()

    assert response["overall_score"] == 78
