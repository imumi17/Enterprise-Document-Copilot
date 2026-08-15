from collections.abc import AsyncIterator
from dataclasses import dataclass

from pydantic_ai.usage import RunUsage

from app.assistant.agent import document_agent
from app.assistant.deps import DocumentAgentDeps
from app.assistant.outputs import GroundedAnswer
from app.config import settings
from app.database.session import async_session_factory
from app.grounding.validator import (
    GroundingValidationResult,
    build_grounding_failure_message,
    validate_grounded_answer,
)
from app.retrieval.retriever import DocumentRetriever

_retriever = DocumentRetriever(async_session_factory)


@dataclass(frozen=True)
class ChatTurnResult:
    grounded_answer: GroundedAnswer
    usage: RunUsage
    validation: GroundingValidationResult


def build_agent_deps(user_id: str, thread_id: str) -> DocumentAgentDeps:
    return DocumentAgentDeps(
        user_id=user_id,
        thread_id=thread_id,
        session_factory=async_session_factory,
        retriever=_retriever,
    )


def usage_to_metadata(usage: RunUsage) -> dict:
    return {
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "requests": usage.requests,
        "model": settings.openai_chat_model,
    }


async def run_agent_turn(user_text: str, deps: DocumentAgentDeps) -> ChatTurnResult:
    async with document_agent.run_stream(user_text, deps=deps) as result:
        async for _ in result.stream_output(debounce_by=0.02):
            pass

        grounded = await result.get_output()
        validation = validate_grounded_answer(grounded, deps.retrieved_chunk_ids)
        return ChatTurnResult(
            grounded_answer=grounded,
            usage=result.usage,
            validation=validation,
        )


async def stream_text_as_deltas(text: str) -> AsyncIterator[str]:
    words = text.split(" ")
    for index, word in enumerate(words):
        yield word if index == 0 else f" {word}"


def response_text_for_turn(turn: ChatTurnResult) -> str:
    if turn.validation.ok:
        return turn.grounded_answer.answer
    return build_grounding_failure_message(turn.validation)
