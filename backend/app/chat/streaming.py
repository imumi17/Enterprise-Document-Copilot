import asyncio
import json
import uuid
from collections.abc import AsyncIterator

UI_MESSAGE_STREAM_HEADERS = {
    "Content-Type": "text/event-stream",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "x-vercel-ai-ui-message-stream": "v1",
}


def format_sse_event(payload: dict) -> str:
    return f"data: {json.dumps(payload, separators=(',', ':'))}\n\n"


async def stream_ui_message_text(
    text: str,
    delay_seconds: float = 0.04,
    message_id: str | None = None,
) -> AsyncIterator[str]:
    message_id = message_id or f"msg_{uuid.uuid4().hex}"
    text_id = f"text_{uuid.uuid4().hex}"

    yield format_sse_event({"type": "start", "messageId": message_id})
    yield format_sse_event({"type": "text-start", "id": text_id})

    words = text.split(" ")
    for index, word in enumerate(words):
        delta = word if index == 0 else f" {word}"
        yield format_sse_event({"type": "text-delta", "id": text_id, "delta": delta})
        await asyncio.sleep(delay_seconds)

    yield format_sse_event({"type": "text-end", "id": text_id})
    yield format_sse_event({"type": "finish"})
    yield "data: [DONE]\n\n"


async def stream_ui_message_deltas(
    deltas: AsyncIterator[str],
    message_id: str | None = None,
) -> AsyncIterator[str]:
    message_id = message_id or f"msg_{uuid.uuid4().hex}"
    text_id = f"text_{uuid.uuid4().hex}"

    yield format_sse_event({"type": "start", "messageId": message_id})
    yield format_sse_event({"type": "text-start", "id": text_id})

    async for delta in deltas:
        if delta:
            yield format_sse_event({"type": "text-delta", "id": text_id, "delta": delta})

    yield format_sse_event({"type": "text-end", "id": text_id})
    yield format_sse_event({"type": "finish"})
    yield "data: [DONE]\n\n"
