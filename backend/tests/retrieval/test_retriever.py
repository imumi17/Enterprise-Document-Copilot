import pytest

from app.database.session import async_session_factory
from app.retrieval.retriever import DocumentRetriever


@pytest.mark.integration
@pytest.mark.asyncio
async def test_retriever_finds_nvidia_data_center_passage():
    retriever = DocumentRetriever(async_session_factory)
    passages = await retriever.search(
        "NVIDIA data center revenue and demand",
        limit=5,
    )

    assert passages
    assert any(
        passage.ticker == "NVDA" and "data center" in passage.text.lower()
        for passage in passages
    )
