from app.assistant.outputs import Citation, GroundedAnswer
from app.grounding.validator import (
    GroundingFailureReason,
    declares_insufficient_evidence,
    validate_grounded_answer,
)


def test_declares_insufficient_evidence():
    assert declares_insufficient_evidence(
        "The corpus does not contain enough information to answer that question."
    )
    assert not declares_insufficient_evidence("Data center revenue was $47.5 billion.")


def test_validate_accepts_insufficient_evidence_without_citations():
    answer = GroundedAnswer(
        answer="The corpus does not contain enough evidence about Mars colonization.",
        citations=[],
    )
    result = validate_grounded_answer(answer, retrieved_chunk_ids=set())
    assert result.ok


def test_validate_rejects_missing_citations():
    answer = GroundedAnswer(
        answer="NVIDIA data center revenue grew 217% in fiscal 2024.",
        citations=[],
    )
    result = validate_grounded_answer(answer, retrieved_chunk_ids={"abc"})
    assert not result.ok
    assert result.reason == GroundingFailureReason.MISSING_CITATIONS


def test_validate_rejects_citation_not_retrieved():
    chunk_id = "00000000-0000-0000-0000-000000000001"
    answer = GroundedAnswer(
        answer="Revenue grew [1].",
        citations=[
            Citation(label="[1]", chunk_id=chunk_id, excerpt="Revenue grew year over year."),
        ],
    )
    result = validate_grounded_answer(answer, retrieved_chunk_ids=set())
    assert not result.ok
    assert result.reason == GroundingFailureReason.CITATION_NOT_RETRIEVED


def test_validate_accepts_retrieved_citations():
    chunk_id = "00000000-0000-0000-0000-000000000001"
    answer = GroundedAnswer(
        answer="Revenue grew [1].",
        citations=[
            Citation(label="[1]", chunk_id=chunk_id, excerpt="Revenue grew year over year."),
        ],
    )
    result = validate_grounded_answer(answer, retrieved_chunk_ids={chunk_id})
    assert result.ok


def test_validate_rejects_invalid_chunk_id():
    answer = GroundedAnswer(
        answer="Revenue grew [1].",
        citations=[
            Citation(label="[1]", chunk_id="not-a-uuid", excerpt="Revenue grew."),
        ],
    )
    result = validate_grounded_answer(answer, retrieved_chunk_ids={"not-a-uuid"})
    assert not result.ok
    assert result.reason == GroundingFailureReason.INVALID_CHUNK_ID
