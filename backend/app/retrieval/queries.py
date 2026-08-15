from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import DocumentChunk, SourceDocument
from app.retrieval.types import RankedChunk

DEFAULT_SEARCH_LIMIT = 20


async def semantic_search(
    session: AsyncSession,
    query_embedding: list[float],
    limit: int = DEFAULT_SEARCH_LIMIT,
) -> list[RankedChunk]:
    distance = DocumentChunk.embedding.cosine_distance(query_embedding)
    stmt = (
        select(DocumentChunk.id, distance.label("distance"))
        .order_by(distance)
        .limit(limit)
    )
    rows = (await session.execute(stmt)).all()
    return [
        RankedChunk(chunk_id=row.id, rank_score=float(row.distance))
        for row in rows
    ]


async def fulltext_search(
    session: AsyncSession,
    query_text: str,
    limit: int = DEFAULT_SEARCH_LIMIT,
) -> list[RankedChunk]:
    ts_query = func.plainto_tsquery("english", query_text)
    rank = func.ts_rank_cd(DocumentChunk.search_vector, ts_query)
    stmt = (
        select(DocumentChunk.id, rank.label("rank"))
        .where(DocumentChunk.search_vector.op("@@")(ts_query))
        .order_by(rank.desc())
        .limit(limit)
    )
    rows = (await session.execute(stmt)).all()
    return [
        RankedChunk(chunk_id=row.id, rank_score=float(row.rank))
        for row in rows
    ]


async def fetch_chunks_by_ids(
    session: AsyncSession,
    chunk_ids: list[UUID],
) -> list[tuple[DocumentChunk, SourceDocument]]:
    if not chunk_ids:
        return []

    stmt = (
        select(DocumentChunk, SourceDocument)
        .join(SourceDocument, DocumentChunk.document_id == SourceDocument.id)
        .where(DocumentChunk.id.in_(chunk_ids))
    )
    rows = (await session.execute(stmt)).all()
    by_id = {chunk.id: (chunk, document) for chunk, document in rows}
    return [by_id[chunk_id] for chunk_id in chunk_ids if chunk_id in by_id]


async def fetch_chunk_with_document(
    session: AsyncSession,
    chunk_id: UUID,
) -> tuple[DocumentChunk, SourceDocument] | None:
    stmt = (
        select(DocumentChunk, SourceDocument)
        .join(SourceDocument, DocumentChunk.document_id == SourceDocument.id)
        .where(DocumentChunk.id == chunk_id)
    )
    row = (await session.execute(stmt)).first()
    if row is None:
        return None
    return row[0], row[1]


async def fetch_surrounding_chunks(
    session: AsyncSession,
    document_id: UUID,
    chunk_index: int,
    before: int,
    after: int,
) -> list[tuple[DocumentChunk, SourceDocument]]:
    min_index = max(0, chunk_index - before)
    max_index = chunk_index + after
    stmt = (
        select(DocumentChunk, SourceDocument)
        .join(SourceDocument, DocumentChunk.document_id == SourceDocument.id)
        .where(
            DocumentChunk.document_id == document_id,
            DocumentChunk.chunk_index >= min_index,
            DocumentChunk.chunk_index <= max_index,
        )
        .order_by(DocumentChunk.chunk_index.asc())
    )
    rows = (await session.execute(stmt)).all()
    return [(chunk, document) for chunk, document in rows]
