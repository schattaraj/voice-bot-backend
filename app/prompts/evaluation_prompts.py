"""LLM prompt for the Evaluation Engine — scoring a completed roleplay
transcript.

Deliberately separate from character_rules.py / persona_prompts.py (Step
14): those put the model in the *customer's* character and forbid it from
ever stepping outside that role. This prompt does the opposite — it puts
the model in a sales-coach/evaluator role, analyzing the transcript from
the outside, after the call is already over.
"""

from app.schemas.transcript import TranscriptTurn

_SPEAKER_LABELS = {"rep": "Salesperson", "ai-buyer": "Customer"}

_OUTPUT_SCHEMA_EXAMPLE = """{
  "overall_score": 78,
  "discovery_score": 65,
  "objection_handling_score": 80,
  "communication_score": 85,
  "closing_score": 70,
  "strengths": ["Specific thing the rep did well", "..."],
  "weaknesses": ["Specific thing the rep could improve", "..."],
  "recommendations": ["Specific, actionable suggestion", "..."]
}"""


def render_evaluator_role() -> str:
    return """<role>
You are an expert B2B sales coach reviewing a completed sales roleplay call. You are
not a participant in the call and were not the customer on it — you are analyzing a
transcript after the fact, purely to produce an objective performance evaluation of
the salesperson.
</role>"""


def render_scoring_rubric() -> str:
    return """<scoring_rubric>
Score each dimension from 0 to 100, based only on the salesperson's performance in the
transcript below:
- discovery_score: how well they uncovered the customer's needs, pain points, and
  situation before pitching a solution.
- objection_handling_score: how effectively they addressed pushback, hesitation, or
  stated objections from the customer.
- communication_score: clarity, active listening, tone, and pacing.
- closing_score: whether they moved the conversation toward a clear, concrete next
  step rather than leaving it open-ended.
- overall_score: your holistic judgment of the call — not simply an average of the
  four scores above.
</scoring_rubric>"""


def render_transcript_section(transcript: list[TranscriptTurn]) -> str:
    if not transcript:
        return "<transcript>\n(empty transcript — no turns were recorded)\n</transcript>"

    lines = [f"{_SPEAKER_LABELS[turn.speaker]}: {turn.text}" for turn in transcript]
    return "<transcript>\n" + "\n".join(lines) + "\n</transcript>"


def render_output_format() -> str:
    return f"""<output_format>
Respond with ONLY a single JSON object — no prose, no markdown code fences, no
commentary before or after it. It must match exactly this shape (the numbers below are
illustrative, not a suggestion of what to output):

{_OUTPUT_SCHEMA_EXAMPLE}

strengths, weaknesses, and recommendations must each be short, specific, and grounded
in what actually happened in the transcript above — not generic sales advice.
</output_format>"""
