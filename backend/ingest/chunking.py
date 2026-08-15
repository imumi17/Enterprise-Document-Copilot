from __future__ import annotations

import re
from dataclasses import dataclass

SECTION_HEADING_PATTERN = re.compile(r"^(ITEM\s+\d+[A-Z]?\.[^\n]*)", re.IGNORECASE | re.MULTILINE)
DEFAULT_CHUNK_SIZE = 1800
DEFAULT_CHUNK_OVERLAP = 200


@dataclass(frozen=True)
class TextChunk:
    chunk_index: int
    text: str
    section: str | None
    token_count: int
    metadata: dict


def estimate_token_count(text: str) -> int:
    words = len(text.split())
    return max(1, int(words * 1.3))


def split_sections(markdown: str) -> list[tuple[str | None, str]]:
    matches = list(SECTION_HEADING_PATTERN.finditer(markdown))
    if not matches:
        return [(None, markdown)]

    sections: list[tuple[str | None, str]] = []
    prefix = markdown[: matches[0].start()].strip()
    if prefix:
        sections.append((None, prefix))

    for index, match in enumerate(matches):
        section_title = match.group(1).strip()
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        body = markdown[start:end].strip()
        if body:
            sections.append((section_title, body))

    return sections


def split_text_window(text: str, chunk_size: int, overlap: int) -> list[str]:
    cleaned = text.strip()
    if not cleaned:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(cleaned):
        end = min(start + chunk_size, len(cleaned))
        if end < len(cleaned):
            space = cleaned.rfind(" ", start, end)
            if space > start + chunk_size // 2:
                end = space
        chunk = cleaned[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(cleaned):
            break
        start = max(end - overlap, start + 1)

    return chunks


def chunk_markdown(
    markdown: str,
    base_metadata: dict,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[TextChunk]:
    chunks: list[TextChunk] = []
    chunk_index = 0

    for section_title, section_text in split_sections(markdown):
        for chunk_text in split_text_window(section_text, chunk_size, chunk_overlap):
            metadata = {
                **base_metadata,
                "section": section_title,
            }
            chunks.append(
                TextChunk(
                    chunk_index=chunk_index,
                    text=chunk_text,
                    section=section_title,
                    token_count=estimate_token_count(chunk_text),
                    metadata=metadata,
                )
            )
            chunk_index += 1

    return chunks
