"""
Bill Extraction Agent Node
Extracts structured financial data from medical bills and pharmacy bills
"""

from datetime import UTC, datetime
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from src.ai.graph.state import BillSchema, ClaimState, ExtractedDocument
from src.ai.prompts import BILL_EXTRACTION_SYSTEM_PROMPT
from src.core.llm import get_default_llm
from src.schema.enum import DocumentType
from src.utils.logger import log


async def bill_extraction_node(state: ClaimState, config: RunnableConfig) -> dict[str, Any]:
    """
    LangGraph Node: Bill Extraction Agent.

    Processes classified bills and pharmacy bills to extract structured
    financial data including invoice numbers, amounts, dates, and hospital info.

    Args:
        state: Current claim processing state with classified documents
        config: LangGraph runtime configuration for tracing

    Returns:
        Dict with extracted_documents key containing list of ExtractedDocument objects

    Note:
        Uses operator.add annotation in ClaimState, so results accumulate
        across multiple extraction nodes (bill, ID card, discharge summary)
    """
    llm = get_default_llm(temperature=0.0)
    structured_llm = llm.with_structured_output(BillSchema)

    target_docs = [
        doc
        for doc in state.classified_docs
        if doc.doc_type in [DocumentType.BILL, DocumentType.PHARMACY_BILL]
    ]

    if not target_docs:
        log.warning("⚠️ No bills found to process in this claim.")
        return {"extracted_documents": []}

    extracted_results: list[ExtractedDocument] = []

    for doc in target_docs:
        filename = doc.filename
        raw_text = doc.raw_text
        doc_type = doc.doc_type

        log.info(f"💰 Extracting data from: {filename} ({doc_type.value})")

        try:
            truncated_text = raw_text[:8000]
            response: BillSchema = await structured_llm.ainvoke(
                [
                    SystemMessage(content=BILL_EXTRACTION_SYSTEM_PROMPT),
                    HumanMessage(
                        content=(
                            f"Document Type: {doc_type.value}\n"
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

            amount_str = (
                f"{response.total_amount} {response.currency}"
                if response.total_amount
                else "amount not found"
            )
            log.info(
                f"✅ Extracted Bill Data: {filename} | "
                f"Invoice: {response.invoice_number or 'N/A'} | "
                f"Amount: {amount_str} | "
                f"Hospital: {response.hospital_name or 'N/A'}"
            )

        except Exception as e:
            log.error(f"❌ Bill extraction failed for {filename}: {e}")

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
