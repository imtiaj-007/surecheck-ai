"""
LangGraph State Definitions
Defines the structure of data flowing through the claim processing graph
"""

import operator
from typing import Annotated, Any

from pydantic import BaseModel, Field

from src.schema.enum import DocStatus, DocumentType, Severity

# ----- Agent-Specific Models (What the LLM produces) -----


class ClassificationSchema(BaseModel):
    """Structure for the output of the document classification agent."""

    doc_type: DocumentType = Field(..., description="The classified type of the document.")
    confidence: float = Field(
        ..., description="Confidence score between 0.0 and 1.0.", ge=0.0, le=1.0
    )
    reasoning: str = Field(
        ..., description="Brief explanation of why this category was chosen based on the text."
    )


class BillSchema(BaseModel):
    """Structured data extracted from medical bills"""

    invoice_number: str | None = Field(None, description="Invoice or bill number")
    hospital_name: str | None = Field(None, description="Hospital or clinic name")
    bill_date: str | None = Field(None, description="Bill date (YYYY-MM-DD)")
    total_amount: float | None = Field(None, description="Total amount to be paid")
    currency: str = Field(default="USD", description="Currency code (ISO 4217)")


class IDCardSchema(BaseModel):
    """Structured data extracted from insurance ID cards"""

    full_name: str | None = Field(None, description="Name as shown on ID card")
    policy_number: str | None = Field(None, description="Insurance policy number")
    date_of_birth: str | None = Field(None, description="Date of birth (YYYY-MM-DD)")
    group_number: str | None = Field(None, description="Group number if applicable")


class DischargeSummarySchema(BaseModel):
    """Structured data extracted from discharge summaries"""

    patient_name: str | None = Field(None, description="Patient name")
    admission_date: str | None = Field(None, description="Admission date (YYYY-MM-DD)")
    discharge_date: str | None = Field(None, description="Discharge date (YYYY-MM-DD)")
    diagnosis: str | None = Field(None, description="Primary diagnosis")
    procedures: list[str] = Field(default_factory=list, description="Medical procedures performed")


# ----- Internal Graph State -----


class DocumentInput(BaseModel):
    """Input document before classification"""

    filename: str
    raw_text: str
    file_size: int | None = None
    upload_timestamp: str | None = None


class ClassifiedDocument(BaseModel):
    """Document after classification"""

    filename: str
    raw_text: str
    doc_type: DocumentType
    reasoning: str
    confidence: float = Field(ge=0.0, le=1.0, description="Classification confidence score")


class ExtractedDocument(BaseModel):
    """Document after data extraction"""

    filename: str
    doc_type: DocumentType
    raw_text: str
    data: dict[str, Any]
    extraction_timestamp: str | None = None


class ValidationIssue(BaseModel):
    """Single validation issue found during verification"""

    severity: Severity
    message: str
    field: str | None = Field(None, description="Specific field with issue")
    doc_type: DocumentType | None = Field(None, description="Document type where issue found")


class ValidationReport(BaseModel):
    """Complete validation report for a claim"""

    missing_documents: list[DocumentType] = Field(
        default_factory=list, description="Required document types that are missing"
    )
    discrepancies: list[ValidationIssue] = Field(
        default_factory=list, description="Data inconsistencies or validation errors"
    )
    status: DocStatus
    validation_timestamp: str | None = None


# ----- The Main Graph State (Passed between nodes) -----


class ClaimState(BaseModel):
    """
    Main state object passed between LangGraph nodes.

    This represents the complete state of a claim as it moves through
    the processing pipeline: classification -> extraction -> validation.
    """

    inputs: list[DocumentInput] = Field(default_factory=list)
    classified_docs: list[ClassifiedDocument] = Field(default_factory=list)
    extracted_documents: Annotated[list[ExtractedDocument], operator.add] = Field(
        default_factory=list
    )
    validation_report: ValidationReport | None = None

    # Metadata
    claim_id: str | None = None
    processing_started_at: str | None = None
    processing_completed_at: str | None = None

    class Config:
        arbitrary_types_allowed = True
