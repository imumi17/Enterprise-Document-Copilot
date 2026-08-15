from dataclasses import dataclass
from uuid import UUID

from pydantic import BaseModel, Field


@dataclass(frozen=True)
class RankedChunk:
    chunk_id: UUID
    rank_score: float


class SourcePassage(BaseModel):
    chunk_id: str
    document_id: str
    chunk_index: int
    text: str
    ticker: str
    company_name: str
    filing_type: str
    filing_date: str
    fiscal_year: int
    accession_number: str
    source_url: str
    section: str | None = None
    page: int | None = None
    score: float = 0.0
    metadata: dict = Field(default_factory=dict)
