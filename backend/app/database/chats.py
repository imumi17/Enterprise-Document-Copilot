import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.outputs import Citation
from app.database.models import ChatMessage, ChatThread, MessageCitation
from app.retrieval.queries import fetch_chunks_by_ids


async def list_threads(session: AsyncSession, user_id: uuid.UUID) -> list[ChatThread]:
    result = await session.execute(
        select(ChatThread)
        .where(ChatThread.user_id == user_id)
        .order_by(ChatThread.updated_at.desc())
    )
    return list(result.scalars().all())


async def create_thread(
    session: AsyncSession,
    user_id: uuid.UUID,
    title: str = "New chat",
) -> ChatThread:
    thread = ChatThread(user_id=user_id, title=title)
    session.add(thread)
    await session.commit()
    await session.refresh(thread)
    return thread


async def get_thread_for_user(
    session: AsyncSession,
    thread_id: uuid.UUID,
    user_id: uuid.UUID,
) -> ChatThread | None:
    result = await session.execute(
        select(ChatThread).where(
            ChatThread.id == thread_id,
            ChatThread.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def list_messages(session: AsyncSession, thread_id: uuid.UUID) -> list[ChatMessage]:
    result = await session.execute(
        select(ChatMessage)
        .where(ChatMessage.thread_id == thread_id)
        .order_by(ChatMessage.sequence.asc())
    )
    return list(result.scalars().all())


async def message_exists_for_ui_id(
    session: AsyncSession,
    thread_id: uuid.UUID,
    ui_message_id: str,
) -> bool:
    messages = await list_messages(session, thread_id)
    return any(message.message.get("id") == ui_message_id for message in messages)


async def next_sequence(session: AsyncSession, thread_id: uuid.UUID) -> int:
    result = await session.execute(
        select(func.max(ChatMessage.sequence)).where(ChatMessage.thread_id == thread_id)
    )
    current_max = result.scalar_one()
    return 0 if current_max is None else current_max + 1


async def append_message(
    session: AsyncSession,
    thread_id: uuid.UUID,
    role: str,
    message: dict,
) -> ChatMessage:
    sequence = await next_sequence(session, thread_id)
    row = ChatMessage(
        thread_id=thread_id,
        role=role,
        message=message,
        sequence=sequence,
    )
    session.add(row)
    await session.execute(
        ChatThread.__table__.update()
        .where(ChatThread.id == thread_id)
        .values(updated_at=func.now())
    )
    await session.commit()
    await session.refresh(row)
    return row


def citation_metadata(chunk, document) -> dict:
    return {
        "ticker": document.ticker,
        "company_name": document.company_name,
        "filing_type": document.filing_type,
        "filing_date": document.filing_date.isoformat(),
        "fiscal_year": document.fiscal_year,
        "accession_number": document.accession_number,
        "source_url": document.source_url,
        "section": chunk.section,
        "page": chunk.page,
        "chunk_index": chunk.chunk_index,
    }


async def enrich_citations_for_storage(
    session: AsyncSession,
    citations: list[Citation],
) -> list[dict]:
    if not citations:
        return []

    chunk_ids = [uuid.UUID(citation.chunk_id) for citation in citations]
    rows = await fetch_chunks_by_ids(session, chunk_ids)
    by_chunk_id = {str(chunk.id): (chunk, document) for chunk, document in rows}

    enriched: list[dict] = []
    for citation in citations:
        data = citation.model_dump()
        chunk_row = by_chunk_id.get(citation.chunk_id)
        if chunk_row is None:
            enriched.append(data)
            continue
        chunk, document = chunk_row
        data.update(citation_metadata(chunk, document))
        data["source_url"] = document.source_url
        data["accession_number"] = document.accession_number
        enriched.append(data)
    return enriched


async def append_assistant_message_with_citations(
    session: AsyncSession,
    thread_id: uuid.UUID,
    message: dict,
    citations: list[Citation],
) -> ChatMessage:
    sequence = await next_sequence(session, thread_id)
    row = ChatMessage(
        thread_id=thread_id,
        role="assistant",
        message=message,
        sequence=sequence,
    )
    session.add(row)
    await session.flush()

    if citations:
        chunk_ids = [uuid.UUID(citation.chunk_id) for citation in citations]
        rows = await fetch_chunks_by_ids(session, chunk_ids)
        by_chunk_id = {str(chunk.id): (chunk, document) for chunk, document in rows}

        for citation in citations:
            chunk_row = by_chunk_id.get(citation.chunk_id)
            if chunk_row is None:
                continue
            chunk, document = chunk_row
            session.add(
                MessageCitation(
                    message_id=row.id,
                    chunk_id=chunk.id,
                    citation_label=citation.label,
                    excerpt=citation.excerpt,
                    metadata_=citation_metadata(chunk, document),
                )
            )

    await session.execute(
        ChatThread.__table__.update()
        .where(ChatThread.id == thread_id)
        .values(updated_at=func.now())
    )
    await session.commit()
    await session.refresh(row)
    return row


async def touch_thread(session: AsyncSession, thread_id: uuid.UUID) -> None:
    await session.execute(
        ChatThread.__table__.update()
        .where(ChatThread.id == thread_id)
        .values(updated_at=func.now())
    )
    await session.commit()
