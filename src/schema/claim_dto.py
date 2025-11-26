from pydantic import BaseModel, Field

from src.schema.enum import DocStatus, DocumentType, Severity


class ClaimDecision(BaseModel):
    """
    Final claim decision, representing the outcome of the validation process.
    """

    status: DocStatus = Field(..., description="Final decision status of the claim")
    reason: str = Field(..., description="Explanation or justification for the decision")
    adjudicator: str | None = Field(
        None, description="Name or ID of the adjudicator (human or AI) that made the decision"
    )
    notes: str | None = Field(
        None, description="Optional notes for manual review or context about the decision"
    )
    explanation: str | None = Field(
        None,
        description="Detailed explanation or structured rationale (could be structured for traceability)",
    )


class ValidationIssue(BaseModel):
    """Single validation issue found during verification"""

    severity: Severity = Field(..., description="Impact level of the discrepancy")
    message: str = Field(..., description="Short description of the issue")
    field: str | None = Field(None, description="Specific field with issue")
    doc_type: DocumentType | None = Field(None, description="Document type where issue found")


class ValidationResponse(BaseModel):
    """Complete validation report for a claim"""

    missing_documents: list[DocumentType] = Field(
        default_factory=list, description="Required document types that are missing"
    )
    discrepancies: list[ValidationIssue] = Field(
        default_factory=list, description="Data inconsistencies or validation errors"
    )
    validation_timestamp: str | None = Field(
        None, description="Timestamp when validation was performed"
    )


class ValidationReport(ValidationResponse):
    status: DocStatus = Field(
        ..., description="Final status after validation (approved/rejected/manual_review)"
    )
    reason: str = Field(..., description="Concise explanation justifying the status")


class ClaimProcessResponse(BaseModel):
    """Claim Response Structure"""

    documents: list[str] = Field(
        ..., description="List of successfully processed document filenames"
    )
    validation: ValidationResponse = Field(..., description="Validation report for the claim")
    claim_decision: ClaimDecision = Field(..., description="Final claim decision details")
