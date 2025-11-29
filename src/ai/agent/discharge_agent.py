"""
Discharge Summary Extraction Agent Node
Extracts clinical data from hospital discharge summaries including
diagnosis, admission/discharge dates, procedures, and patient information
"""

from datetime import UTC, datetime
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langsmith import traceable

from src.ai.graph.state import ClaimState, DischargeSummarySchema, ExtractedDocument
from src.ai.prompts import DISCHARGE_EXTRACTION_SYSTEM_PROMPT
from src.core.llm import get_default_llm
from src.schema.enum import DocumentType
from src.utils.logger import log


@traceable(
    name="discharge_extraction_agent",
    tags=["dimension:language", "node:discharge_extraction"],
    metadata={"dimension": "language", "component": "DischargeSummaryExtractionNode"},
)
async def discharge_extraction_node(state: ClaimState, config: RunnableConfig) -> dict[str, Any]:
    """
    LangGraph Node: Discharge Summary Extraction Agent.

    Processes discharge summaries to extract clinical and administrative data
    including patient info, admission/discharge dates, diagnosis, procedures,
    and treatment details.

    Args:
        state: Current claim processing state with classified documents
        config: LangGraph runtime configuration for tracing

    Returns:
        Dict with extracted_documents key containing list of ExtractedDocument objects

    Note:
        Discharge summaries are typically the longest documents and contain
        critical clinical information needed for claim validation.
    """
    llm = get_default_llm(temperature=0.0)
    structured_llm = llm.with_structured_output(DischargeSummarySchema)

    target_docs = [
        doc for doc in state.classified_docs if doc.doc_type == DocumentType.DISCHARGE_SUMMARY
    ]

    if not target_docs:
        log.info("⚠️ No discharge summaries found to process in this claim.")
        return {"extracted_documents": []}

    extracted_results: list[ExtractedDocument] = []

    for doc in target_docs:
        filename = doc.filename
        raw_text = doc.raw_text
        doc_type = doc.doc_type

        log.info(f"🏥 Extracting clinical data from: {filename}")

        try:
            truncated_text = raw_text[:15000]
            response: DischargeSummarySchema = await structured_llm.ainvoke(
                [
                    SystemMessage(content=DISCHARGE_EXTRACTION_SYSTEM_PROMPT),
                    HumanMessage(
                        content=(
                            f"Document Type: Discharge Summary\n"
                            f"Filename: {filename}\n\n"
                            f"Document Content:\n{truncated_text}"
                        )
                    ),
                ],
                config=config,
            )

            extracted_doc = ExtractedDocument(
                filename=filename,
                doc_type=doc_type,
                raw_text=raw_text,
                data=response.model_dump(exclude_none=True),
                extraction_timestamp=datetime.now(UTC).isoformat(),
            )
            extracted_results.append(extracted_doc)

            log.info(
                f"✅ Extracted Discharge Summary: {filename} | "
                f"Patient: {response.patient_name or 'N/A'} | "
                f"Admission: {response.admission_date or 'N/A'} | "
                f"Discharge: {response.discharge_date or 'N/A'}"
                f"Diagnosis: {response.diagnosis or 'N/A'} | "
            )

        except Exception as e:
            log.error(f"❌ Discharge Extraction Failed for {filename}: {e}")
            extracted_doc = ExtractedDocument(
                filename=filename,
                doc_type=doc_type,
                raw_text=raw_text,
                data={
                    "extraction_error": str(e),
                    "error_type": type(e).__name__,
                },
                extraction_timestamp=datetime.now(UTC).isoformat(),
            )
            extracted_results.append(extracted_doc)

    return {"extracted_documents": extracted_results}
