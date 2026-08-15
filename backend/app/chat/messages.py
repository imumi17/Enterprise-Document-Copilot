from typing import Any


def ui_message_to_storage(message: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": message.get("id"),
        "role": message.get("role"),
        "parts": message.get("parts", []),
    }


def storage_to_ui_message(message: dict[str, Any]) -> dict[str, Any]:
    stored: dict[str, Any] = {
        "id": str(message.get("id")),
        "role": message.get("role"),
        "parts": message.get("parts", []),
    }
    metadata = message.get("metadata")
    if isinstance(metadata, dict):
        stored["metadata"] = metadata
    return stored


def extract_text_from_ui_message(message: dict[str, Any]) -> str:
    parts = message.get("parts")
    if isinstance(parts, list):
        texts = [
            part.get("text", "")
            for part in parts
            if isinstance(part, dict) and part.get("type") == "text"
        ]
        joined = "".join(texts).strip()
        if joined:
            return joined

    content = message.get("content")
    if isinstance(content, str):
        return content.strip()

    return ""


def build_assistant_message(message_id: str, text: str) -> dict[str, Any]:
    return {
        "id": message_id,
        "role": "assistant",
        "parts": [{"type": "text", "text": text}],
    }


def build_assistant_message_with_metadata(
    message_id: str,
    text: str,
    citations: list[dict[str, Any]],
    usage: dict[str, Any],
    grounding_failed: bool = False,
) -> dict[str, Any]:
    message = build_assistant_message(message_id, text)
    message["metadata"] = {
        "citations": citations,
        "usage": usage,
        "grounding_failed": grounding_failed,
    }
    return message


def is_trading_advice_request(user_text: str) -> bool:
    lowered = user_text.lower()
    return any(
        phrase in lowered
        for phrase in (
            "buy or sell",
            "should i buy",
            "should i sell",
            "should we buy",
            "should we sell",
            "stock pick",
            "trading recommendation",
            "investment advice",
        )
    )


def build_trading_advice_refusal() -> str:
    return (
        "I can't provide buy, sell, or hold recommendations. Document Copilot "
        "answers questions grounded in SEC filings only—not trading advice. "
        "Ask what the filings disclose (for example revenue mix, risk factors, "
        "or segment performance) and I'll cite the source passages."
    )
