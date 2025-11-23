from pydantic import BaseModel, Field

from src.schema.enum import DocumentType


class ClassificationOutput(BaseModel):
    """Structure for the output of the document classification agent."""

    doc_type: DocumentType = Field(..., description="The classified type of the document.")
    confidence: float = Field(
        ..., description="Confidence score between 0.0 and 1.0.", ge=0.0, le=1.0
    )
    reasoning: str = Field(
        ..., description="Brief explanation of why this category was chosen based on the text."
    )
