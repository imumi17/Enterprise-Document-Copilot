from pydantic import BaseModel, Field


class Citation(BaseModel):
    label: str = Field(description="Inline citation label, e.g. [1]")
    chunk_id: str = Field(description="UUID of the cited document chunk")
    excerpt: str = Field(description="Short excerpt from the chunk supporting the claim")


class GroundedAnswer(BaseModel):
    answer: str
    citations: list[Citation] = Field(default_factory=list)
