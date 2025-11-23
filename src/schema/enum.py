from enum import Enum


class DocType(str, Enum):
    BILL = "bill"
    ID_CARD = "id_card"
    DISCHARGE_SUMMARY = "discharge_summary"
    UNKNOWN = "unknown"


class Severity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"


class DocStatus(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    MANUAL_REVIEW = "manual_review"
