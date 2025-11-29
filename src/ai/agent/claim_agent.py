"""
Claim Validation Agent Node
This node receives the full set of extracted documents and orchestrates
LLM-based final validation to ensure reliable claim adjudication.
"""

from datetime import UTC, datetime
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langsmith import traceable

from src.ai.graph.state import ClaimState
from src.ai.prompts import CLAIM_VALIDATION_SYSTEM_PROMPT
from src.core.llm import get_default_llm
from src.schema.claim_dto import ValidationIssue, ValidationReport
from src.schema.enum import DocStatus, Severity
from src.utils.logger import log


@traceable(
    name="claim_validation_agent",
    tags=["dimension:language", "node:claim_validation"],
    metadata={"dimension": "language", "component": "ClaimValidationNode"},
)
async def claim_validation_node(state: ClaimState, config: RunnableConfig) -> dict[str, Any]:
    """
    LangGraph Node: Claim Validation ("The Judge").

    This node performs the final validation and adjudication logic for an insurance claim.
    It compiles all structured data extracted from bills, discharge summaries, and ID cards,
    then uses an LLM to check for document completeness, cross-document consistency,
    plausible dates, and suspected fraud.

    - Accepts all ExtractedDocument objects for the current claim (state.extracted_documents).
    - Evaluates the claim with the LLM using structured output (ValidationReport schema).
    - Captures the validation status, details any discrepancies, and lists missing documents.
    - Handles exceptions and triggers a manual review status in case of errors.

    Args:
        state (ClaimState): The graph state containing extracted documents.
        config (RunnableConfig): Runtime configuration for LLM tracing and control.

    Returns:
        Dict containing the generated ValidationReport object
    """
    context_data: list[dict[str, Any]] = []
    for doc in state.extracted_documents:
        context_data.append(
            {"file_name": doc.filename, "file_type": doc.doc_type, "extracted_data": doc.data}
        )

    log.info("⚖️  Validating Claim consistency...")

    llm = get_default_llm(temperature=0.0)
    structured_llm = llm.with_structured_output(ValidationReport)

    try:
        response: ValidationReport = await structured_llm.ainvoke(
            [
                SystemMessage(content=CLAIM_VALIDATION_SYSTEM_PROMPT),
                HumanMessage(content=f"Extracted Documents:\n{context_data}"),
            ],
            config=config,
        )

        claim_result = ValidationReport(
            status=response.status,
            reason=response.reason,
            discrepancies=response.discrepancies,
            missing_documents=response.missing_documents,
            validation_timestamp=datetime.now(UTC).isoformat(),
        )
        log.info(f"🔮 Final Decision: {response.status.value}")

        return {"validation_report": claim_result}

    except Exception as e:
        log.error(f"Validation failed: {e}")
        return {
            "validation_report": ValidationReport(
                status=DocStatus.MANUAL_REVIEW,
                reason="Validation could not be completed due to an internal error. Please review manually.",
                discrepancies=[
                    ValidationIssue(severity=Severity.HIGH, message=f"AI Validation Error: {e!s}")
                ],
                missing_documents=[],
                validation_timestamp=datetime.now(UTC).isoformat(),
            )
        }
