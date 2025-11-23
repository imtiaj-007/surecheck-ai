import operator
from typing import Annotated, Any, TypedDict

from pydantic import BaseModel, Field

from src.schema.enum import DocStatus, DocumentType, Severity

# Agent-Specific Models (What the LLM produces)


class BillSchema(BaseModel):
    invoice_number: str | None = Field(description="The invoice or bill number")
    hospital_name: str | None = Field(description="Name of the hospital or clinic")
    bill_date: str | None = Field(description="Date of the bill (YYYY-MM-DD)")
    total_amount: float | None = Field(description="The final total amount to be paid")
    currency: str = Field(default="USD", description="Currency code")


class IDCardSchema(BaseModel):
    full_name: str | None = Field(description="Name exactly as on the ID")
    policy_number: str | None = Field(description="Insurance policy number")
    date_of_birth: str | None = Field(description="DOB (YYYY-MM-DD)")


class DischargeSummarySchema(BaseModel):
    patient_name: str | None = Field(description="Name of the patient")
    admission_date: str | None = Field(description="Date of admission")
    discharge_date: str | None = Field(description="Date of discharge")
    diagnosis: str | None = Field(description="Primary diagnosis or reason for admission")


# Internal Graph State


class ExtractedDocument(BaseModel):
    """Represents a single processed document"""

    file_name: str
    doc_type: DocumentType
    raw_text: str
    data: dict[str, Any]


class ValidationIssue(BaseModel):
    severity: Severity
    message: str


class ValidationReport(BaseModel):
    missing_documents: list[str] = []
    discrepancies: list[ValidationIssue] = []
    status: DocStatus


# The Main Graph State (Passed between nodes)


class ClaimState(TypedDict):
    inputs: list[dict[str, Any]]
    classified_docs: list[dict[str, Any]]
    extracted_documents: Annotated[list[ExtractedDocument], operator.add]
    validation_report: ValidationReport | None
