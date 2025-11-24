from enum import Enum


class DocumentType(str, Enum):
    BILL = "bill"
    DISCHARGE_SUMMARY = "discharge_summary"
    ID_CARD = "id_card"
    PHARMACY_BILL = "pharmacy_bill"
    CLAIM_FORM = "claim_form"
    OTHER = "other"


class DocStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    APPROVED = "approved"
    REJECTED = "rejected"
    MANUAL_REVIEW = "manual_review"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
