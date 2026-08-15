import uuid
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import ensure_profile, get_current_user
from app.auth.models import CurrentUser
from app.chat.messages import (
    build_assistant_message_with_metadata,
    build_trading_advice_refusal,
    extract_text_from_ui_message,
    is_trading_advice_request,
    storage_to_ui_message,
    ui_message_to_storage,
)
from app.chat.orchestrator import (
    build_agent_deps,
    response_text_for_turn,
    run_agent_turn,
    stream_text_as_deltas,
    usage_to_metadata,
)
from app.chat.schemas import (
    ChatStreamRequest,
    ChatThreadResponse,
    ThreadMessagesResponse,
    UiMessage,
)
from app.chat.streaming import (
    UI_MESSAGE_STREAM_HEADERS,
    stream_ui_message_deltas,
    stream_ui_message_text,
)
from app.database.chats import (
    append_assistant_message_with_citations,
    append_message,
    create_thread,
    get_thread_for_user,
    list_messages,
    list_threads,
    message_exists_for_ui_id,
)
from app.database.models import ChatThread
from app.database.session import async_session_factory, get_db_session

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


def thread_to_response(thread: ChatThread) -> ChatThreadResponse:
    return ChatThreadResponse(
        id=str(thread.id),
        title=thread.title,
        created_at=thread.created_at.isoformat(),
        updated_at=thread.updated_at.isoformat(),
    )


@router.get("/threads")
async def read_threads(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[ChatThreadResponse]:
    ensure_profile(user)
    threads = await list_threads(session, uuid.UUID(user.id))
    return [thread_to_response(thread) for thread in threads]


@router.post("/threads", status_code=status.HTTP_201_CREATED)
async def create_chat_thread(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ChatThreadResponse:
    ensure_profile(user)
    thread = await create_thread(session, uuid.UUID(user.id))
    return thread_to_response(thread)


@router.get("/threads/{thread_id}/messages")
async def read_thread_messages(
    thread_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ThreadMessagesResponse:
    thread = await get_thread_for_user(session, thread_id, uuid.UUID(user.id))
    if thread is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")

    rows = await list_messages(session, thread_id)
    messages = [
        UiMessage.model_validate(storage_to_ui_message(row.message)) for row in rows
    ]
    return ThreadMessagesResponse(messages=messages)


@router.post("/stream")
async def stream_chat(
    body: ChatStreamRequest,
    user: CurrentUser = Depends(get_current_user),
) -> StreamingResponse:
    try:
        thread_id = uuid.UUID(body.id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid thread id",
        )

    if not body.messages:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Messages are required",
        )

    async with async_session_factory() as session:
        thread = await get_thread_for_user(session, thread_id, uuid.UUID(user.id))
        if thread is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")

        last_message: dict[str, Any] = body.messages[-1]
        if last_message.get("role") != "user":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Last message must be a user message",
            )

        user_text = extract_text_from_ui_message(last_message)
        if not user_text:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="User message text is required",
            )

        ui_message_id = str(last_message.get("id", ""))
        if ui_message_id and not await message_exists_for_ui_id(
            session, thread_id, ui_message_id
        ):
            await append_message(
                session,
                thread_id,
                "user",
                ui_message_to_storage(last_message),
            )

    assistant_message_id = f"msg_{uuid.uuid4().hex}"

    async def event_stream():
        try:
            if is_trading_advice_request(user_text):
                refusal = build_trading_advice_refusal()
                async for chunk in stream_ui_message_text(
                    refusal,
                    message_id=assistant_message_id,
                ):
                    yield chunk

                async with async_session_factory() as persist_session:
                    await append_message(
                        persist_session,
                        thread_id,
                        "assistant",
                        build_assistant_message_with_metadata(
                            assistant_message_id,
                            refusal,
                            citations=[],
                            usage={
                                "model": None,
                                "input_tokens": 0,
                                "output_tokens": 0,
                                "requests": 0,
                            },
                        ),
                    )
                return

            deps = build_agent_deps(user.id, str(thread_id))
            turn_result = await run_agent_turn(user_text, deps)
            response_text = response_text_for_turn(turn_result)
            grounding_failed = not turn_result.validation.ok

            if grounding_failed:
                logger.warning(
                    "grounding_validation_failed",
                    thread_id=str(thread_id),
                    reason=turn_result.validation.reason,
                    detail=turn_result.validation.detail,
                )

            async for chunk in stream_ui_message_deltas(
                stream_text_as_deltas(response_text),
                message_id=assistant_message_id,
            ):
                yield chunk

            usage = usage_to_metadata(turn_result.usage)
            citations = (
                []
                if grounding_failed
                else [citation.model_dump() for citation in turn_result.grounded_answer.citations]
            )
            message_payload = build_assistant_message_with_metadata(
                assistant_message_id,
                response_text,
                citations=citations,
                usage=usage,
                grounding_failed=grounding_failed,
            )

            async with async_session_factory() as persist_session:
                if grounding_failed:
                    await append_message(
                        persist_session,
                        thread_id,
                        "assistant",
                        message_payload,
                    )
                else:
                    enriched_citations = await enrich_citations_for_storage(
                        persist_session,
                        turn_result.grounded_answer.citations,
                    )
                    message_payload["metadata"]["citations"] = enriched_citations
                    await append_assistant_message_with_citations(
                        persist_session,
                        thread_id,
                        message_payload,
                        turn_result.grounded_answer.citations,
                    )
        except Exception:
            logger.exception("chat_stream_failed", thread_id=str(thread_id))
            raise

    return StreamingResponse(event_stream(), headers=UI_MESSAGE_STREAM_HEADERS)
