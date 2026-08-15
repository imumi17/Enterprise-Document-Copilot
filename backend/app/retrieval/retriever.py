import asyncio
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.retrieval.fusion import reciprocal_rank_fusion
from app.retrieval.queries import (
    DEFAULT_SEARCH_LIMIT,
    fetch_chunks_by_ids,
    fulltext_search,
    semantic_search,
)
from app.retrieval.types import SourcePassage
from ingest.embeddings import embed_texts


class DocumentRetriever:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def search(
        self,
        query: str,
        limit: int = 10,
        search_limit: int = DEFAULT_SEARCH_LIMIT,
    ) -> list[SourcePassage]:
        query_embedding = await asyncio.to_thread(embed_texts, [query])
        if not query_embedding:
            return []

        async with self._session_factory() as session:
            semantic_ranked = await semantic_search(
                session, query_embedding[0], limit=search_limit
            )
            lexical_ranked = await fulltext_search(session, query, limit=search_limit)

            fused = reciprocal_rank_fusion(
                [
                    [item.chunk_id for item in semantic_ranked],
                    [item.chunk_id for item in lexical_ranked],
                ]
            )[:limit]

            if not fused:
                return []

            chunk_ids = [chunk_id for chunk_id, _ in fused]
            score_by_id = {chunk_id: score for chunk_id, score in fused}
            rows = await fetch_chunks_by_ids(session, chunk_ids)

            passages: list[SourcePassage] = []
            for chunk, document in rows:
                metadata = dict(chunk.metadata_ or {})
                passages.append(
                    SourcePassage(
                        chunk_id=str(chunk.id),
                        document_id=str(document.id),
                        chunk_index=chunk.chunk_index,
                        text=chunk.chunk_text,
                        ticker=document.ticker,
                        company_name=document.company_name,
                        filing_type=document.filing_type,
                        filing_date=document.filing_date.isoformat(),
                        fiscal_year=document.fiscal_year,
                        accession_number=document.accession_number,
                        source_url=document.source_url,
                        section=chunk.section,
                        page=chunk.page,
                        score=score_by_id.get(chunk.id, 0.0),
                        metadata=metadata,
                    )
                )

            return passages
