"""Prompt sections driven by where the call currently stands: situational
guidance from ConversationState, and the prior transcript for continuity.
"""

from app.schemas.conversation import ConversationState
from app.schemas.transcript import TranscriptTurn

_SPEAKER_LABELS = {"rep": "Salesperson", "ai-buyer": "You"}


def render_conversation_state_section(state: ConversationState) -> str:
    if state.turn_count == 0 or state.status == "idle":
        guidance = (
            "This call has just started. Answer naturally, as if you've just picked up "
            "an unexpected call — you don't yet know why the salesperson is calling."
        )
    elif state.status == "completed":
        guidance = (
            "This call is wrapping up. Bring the conversation to a natural close "
            "consistent with your stance so far, without suddenly changing your mind."
        )
    else:
        guidance = (
            "This call is in progress. Continue the conversation naturally, responding "
            "to the salesperson's most recent message below."
        )

    return f"""<conversation_state>
Turn count: {state.turn_count}
Elapsed time: {state.elapsed_seconds} seconds
Guidance: {guidance}
</conversation_state>"""


def render_transcript_section(transcript: list[TranscriptTurn]) -> str:
    if not transcript:
        return """<conversation_history>
(No prior messages — this is the start of the call.)
</conversation_history>"""

    lines = [f"{_SPEAKER_LABELS[turn.speaker]}: {turn.text}" for turn in transcript]
    return "<conversation_history>\n" + "\n".join(lines) + "\n</conversation_history>"
