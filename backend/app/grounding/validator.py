from enum import Enum
from uuid import UUID

from app.assistant.outputs import GroundedAnswer

INSUFFICIENT_EVIDENCE_PHRASES = (
    "does not contain enough",
    "do not contain enough",
    "not contain enough",
    "insufficient evidence",
    "not enough information",
    "not enough evidence",
    "cannot answer",
    "can't answer",
    "unable to answer",
    "no relevant",
    "could not find",
    "couldn't find",
)


class GroundingFailureReason(str, Enum):
    MISSING_CITATIONS = "missing_citations"
    INVALID_CHUNK_ID = "invalid_chunk_id"
    CITATION_NOT_RETRIEVED = "citation_not_retrieved"
    CHUNK_NOT_FOUND = "chunk_not_found"


class GroundingValidationResult:
    def __init__(
        self,
        ok: bool,
        reason: GroundingFailureReason | None = None,
        detail: str | None = None,
    ) -> None:
        self.ok = ok
        self.reason = reason
        self.detail = detail


def declares_insufficient_evidence(answer: str) -> bool:
    lowered = answer.lower()
    return any(phrase in lowered for phrase in INSUFFICIENT_EVIDENCE_PHRASES)


def build_grounding_failure_message(result: GroundingValidationResult) -> str:
    if result.reason == GroundingFailureReason.MISSING_CITATIONS:
        return (
            "I couldn't verify that answer against retrieved filing passages because "
            "it did not include citations. Please try a more specific question about "
            "what the filings disclose."
        )
    if result.reason == GroundingFailureReason.CITATION_NOT_RETRIEVED:
        return (
            "I couldn't verify the citations in that answer against retrieved filing "
            "passages. Please try rephrasing your question or asking about a more "
            "specific topic in the filings."
        )
    return (
        "I couldn't verify that answer against retrieved filing passages. "
        "Please try rephrasing your question."
    )


def validate_grounded_answer(
    answer: GroundedAnswer,
    retrieved_chunk_ids: set[str],
) -> GroundingValidationResult:
    if declares_insufficient_evidence(answer.answer):
        return GroundingValidationResult(ok=True)

    if not answer.citations:
        return GroundingValidationResult(
            ok=False,
            reason=GroundingFailureReason.MISSING_CITATIONS,
            detail="Answer has no citations and does not declare insufficient evidence",
        )

    for citation in answer.citations:
        try:
            parsed_id = UUID(citation.chunk_id)
        except ValueError:
            return GroundingValidationResult(
                ok=False,
                reason=GroundingFailureReason.INVALID_CHUNK_ID,
                detail=f"Invalid chunk_id: {citation.chunk_id}",
            )

        if citation.chunk_id not in retrieved_chunk_ids:
            return GroundingValidationResult(
                ok=False,
                reason=GroundingFailureReason.CITATION_NOT_RETRIEVED,
                detail=f"Chunk {citation.chunk_id} was not retrieved in this turn",
            )

        if not citation.excerpt.strip():
            return GroundingValidationResult(
                ok=False,
                reason=GroundingFailureReason.MISSING_CITATIONS,
                detail=f"Citation {citation.label} has an empty excerpt",
            )

        if str(parsed_id) != citation.chunk_id:
            return GroundingValidationResult(
                ok=False,
                reason=GroundingFailureReason.INVALID_CHUNK_ID,
                detail=f"Malformed chunk_id: {citation.chunk_id}",
            )

    return GroundingValidationResult(ok=True)
