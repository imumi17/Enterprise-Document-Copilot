from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.retrieval.retriever import DocumentRetriever


@dataclass
class DocumentAgentDeps:
    user_id: str
    thread_id: str
    session_factory: async_sessionmaker[AsyncSession]
    retriever: DocumentRetriever
    retrieved_chunk_ids: set[str] = field(default_factory=set)
