from __future__ import annotations

import re
from html import unescape

_BLOCK_BREAK_PATTERN = re.compile(
    r"</(p|div|tr|h[1-6]|li|br|table|section|article)>",
    flags=re.IGNORECASE,
)
_BR_PATTERN = re.compile(r"<br\s*/?>", flags=re.IGNORECASE)
_TAG_PATTERN = re.compile(r"<[^>]+>")
_HIDDEN_DIV_PATTERN = re.compile(
    r"<div[^>]*style=\"display:none\"[^>]*>.*?</div>",
    flags=re.IGNORECASE | re.DOTALL,
)
_SCRIPT_STYLE_PATTERN = re.compile(
    r"<(script|style)[^>]*>.*?</\1>",
    flags=re.IGNORECASE | re.DOTALL,
)


def html_to_markdown(html_bytes: bytes) -> str:
    text = html_bytes.decode("utf-8", errors="replace")
    text = _SCRIPT_STYLE_PATTERN.sub("", text)
    text = _HIDDEN_DIV_PATTERN.sub("", text)
    text = _BR_PATTERN.sub("\n", text)
    text = _BLOCK_BREAK_PATTERN.sub("\n", text)
    text = _TAG_PATTERN.sub("", text)
    text = unescape(text)

    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n\n".join(lines)
