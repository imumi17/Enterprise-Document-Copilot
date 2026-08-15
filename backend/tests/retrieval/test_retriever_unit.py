from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

from app.database.models import DocumentChunk, SourceDocument
from app.retrieval.retriever import DocumentRetriever
from app.retrieval.types import RankedChunk


def _fixture_rows() -> list[tuple[DocumentChunk, SourceDocument]]:
    document_id = UUID("00000000-0000-0000-0000-000000000010")
    chunk_a = UUID("00000000-0000-0000-0000-000000000001")
    chunk_b = UUID("00000000-0000-0000-0000-000000000002")

    document = SourceDocument(
        id=document_id,
        ticker="NVDA",
        company_name="NVIDIA Corporation",
        filing_type="10-K",
        filing_date=date(2025, 2, 26),
        fiscal_year=2025,
        accession_number="0001045810-25-000023",
        source_url="https://example.com/nvda-10k",
        markdown_content="",
        metadata_={},
    )
    chunks = [
        DocumentChunk(
            id=chunk_a,
            document_id=document_id,
            chunk_index=0,
            chunk_text="Data center revenue grew driven by AI demand.",
            page=12,
            section="ITEM 7",
            token_count=10,
            metadata_={"ticker": "NVDA"},
            embedding=[0.0] * 1536,
        ),
        DocumentChunk(
            id=chunk_b,
            document_id=document_id,
            chunk_index=1,
            chunk_text="Gaming revenue declined year over year.",
            page=13,
            section="ITEM 7",
            token_count=8,
            metadata_={"ticker": "NVDA"},
            embedding=[0.0] * 1536,
        ),
    ]
    return [(chunks[0], document), (chunks[1], document)]


async def test_retriever_fuses_semantic_and_lexical_results():
    chunk_a = UUID("00000000-0000-0000-0000-000000000001")
    chunk_b = UUID("00000000-0000-0000-0000-000000000002")
    fixture_rows = _fixture_rows()

    session = AsyncMock()
    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=None)
    session_factory = MagicMock(return_value=session_cm)

    retriever = DocumentRetriever(session_factory)

    with (
        patch(
            "app.retrieval.retriever.embed_texts",
            return_value=[[0.1] * 1536],
        ),
        patch(
            "app.retrieval.retriever.semantic_search",
            new_callable=AsyncMock,
            return_value=[
                RankedChunk(chunk_id=chunk_b, rank_score=0.2),
                RankedChunk(chunk_id=chunk_a, rank_score=0.4),
            ],
        ),
        patch(
            "app.retrieval.retriever.fulltext_search",
            new_callable=AsyncMock,
            return_value=[
                RankedChunk(chunk_id=chunk_b, rank_score=0.9),
                RankedChunk(chunk_id=chunk_a, rank_score=0.5),
            ],
        ),
        patch(
            "app.retrieval.retriever.fetch_chunks_by_ids",
            new_callable=AsyncMock,
            side_effect=lambda session, chunk_ids: [
                next(row for row in fixture_rows if row[0].id == chunk_id)
                for chunk_id in chunk_ids
            ],
        ),
    ):
        passages = await retriever.search("data center revenue", limit=2)

    assert len(passages) == 2
    assert passages[0].chunk_id == str(chunk_b)
    assert passages[0].ticker == "NVDA"
    assert "data center" in passages[1].text.lower()
    assert passages[0].score > passages[1].score
