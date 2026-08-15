from pathlib import Path
from uuid import UUID

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.assistant.deps import DocumentAgentDeps
from app.assistant.outputs import GroundedAnswer
from app.config import settings
from app.retrieval.queries import fetch_chunk_with_document, fetch_surrounding_chunks
from app.retrieval.types import SourcePassage

MAX_SURROUNDING_CHUNKS = 2
MAX_CHUNK_TEXT_CHARS = 8000
MAX_SEARCH_EXCERPT_CHARS = 500

_INSTRUCTIONS_PATH = Path(__file__).parent / "instructions.md"


def load_instructions() -> str:
    return _INSTRUCTIONS_PATH.read_text(encoding="utf-8")


def build_chat_model() -> OpenAIChatModel:
    return OpenAIChatModel(
        settings.openai_chat_model,
        provider=OpenAIProvider(api_key=settings.openai_api_key),
    )


def passage_to_summary(passage: SourcePassage) -> dict:
    text = passage.text
    if len(text) > MAX_SEARCH_EXCERPT_CHARS:
        excerpt = text[:MAX_SEARCH_EXCERPT_CHARS] + "…"
    else:
        excerpt = text

    return {
        "chunk_id": passage.chunk_id,
        "ticker": passage.ticker,
        "company_name": passage.company_name,
        "filing_type": passage.filing_type,
        "filing_date": passage.filing_date,
        "fiscal_year": passage.fiscal_year,
        "section": passage.section,
        "page": passage.page,
        "score": passage.score,
        "excerpt": excerpt,
    }


def chunk_row_to_tool_dict(chunk, document) -> dict:
    text = chunk.chunk_text
    if len(text) > MAX_CHUNK_TEXT_CHARS:
        text = text[:MAX_CHUNK_TEXT_CHARS] + "…"

    return {
        "chunk_id": str(chunk.id),
        "document_id": str(document.id),
        "chunk_index": chunk.chunk_index,
        "ticker": document.ticker,
        "company_name": document.company_name,
        "filing_type": document.filing_type,
        "filing_date": document.filing_date.isoformat(),
        "fiscal_year": document.fiscal_year,
        "accession_number": document.accession_number,
        "source_url": document.source_url,
        "section": chunk.section,
        "page": chunk.page,
        "text": text,
    }


document_agent = Agent(
    build_chat_model(),
    deps_type=DocumentAgentDeps,
    output_type=GroundedAnswer,
    system_prompt=load_instructions(),
    retries=2,
)


@document_agent.tool
async def search_filings(
    ctx: RunContext[DocumentAgentDeps],
    query: str,
    limit: int = 10,
) -> list[dict]:
    """Search ingested SEC filing chunks using hybrid semantic and keyword retrieval."""
    limit = max(1, min(limit, 20))
    passages = await ctx.deps.retriever.search(query, limit=limit)
    for passage in passages:
        ctx.deps.retrieved_chunk_ids.add(passage.chunk_id)
    return [passage_to_summary(passage) for passage in passages]


@document_agent.tool
async def read_chunk(ctx: RunContext[DocumentAgentDeps], chunk_id: str) -> dict:
    """Read the full text and metadata for a single filing chunk."""
    try:
        parsed_id = UUID(chunk_id)
    except ValueError:
        return {"error": "Invalid chunk_id"}

    async with ctx.deps.session_factory() as session:
        row = await fetch_chunk_with_document(session, parsed_id)
        if row is None:
            return {"error": "Chunk not found"}

        chunk, document = row
        ctx.deps.retrieved_chunk_ids.add(str(chunk.id))
        return chunk_row_to_tool_dict(chunk, document)


@document_agent.tool
async def read_surrounding_chunks(
    ctx: RunContext[DocumentAgentDeps],
    chunk_id: str,
    before: int = 1,
    after: int = 1,
) -> list[dict]:
    """Read neighboring chunks from the same filing around a given chunk."""
    try:
        parsed_id = UUID(chunk_id)
    except ValueError:
        return [{"error": "Invalid chunk_id"}]

    before = max(0, min(before, MAX_SURROUNDING_CHUNKS))
    after = max(0, min(after, MAX_SURROUNDING_CHUNKS))

    async with ctx.deps.session_factory() as session:
        anchor = await fetch_chunk_with_document(session, parsed_id)
        if anchor is None:
            return [{"error": "Chunk not found"}]

        chunk, _ = anchor
        rows = await fetch_surrounding_chunks(
            session,
            chunk.document_id,
            chunk.chunk_index,
            before=before,
            after=after,
        )

        results: list[dict] = []
        for surrounding_chunk, document in rows:
            ctx.deps.retrieved_chunk_ids.add(str(surrounding_chunk.id))
            results.append(chunk_row_to_tool_dict(surrounding_chunk, document))
        return results
