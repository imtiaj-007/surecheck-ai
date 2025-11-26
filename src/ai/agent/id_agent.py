"""
ID Card Extraction Agent Node
Extracts insurance policy holder information from ID cards including
policy numbers, member details, coverage information, and provider data
"""

from datetime import UTC, datetime
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from src.ai.graph.state import ClaimState, ExtractedDocument, IDCardSchema
from src.ai.prompts import ID_CARD_EXTRACTION_SYSTEM_PROMPT
from src.core.llm import get_default_llm
from src.schema.enum import DocumentType
from src.utils.logger import log


async def id_extraction_node(state: ClaimState, config: RunnableConfig) -> dict[str, Any]:
    """
    LangGraph Node: ID Card Extraction Agent.

    Processes insurance ID cards to extract policy holder information,
    insurance details, coverage data, and provider information needed
    for claim verification and validation.

    Args:
        state: Current claim processing state with classified documents
        config: LangGraph runtime configuration for tracing

    Returns:
        Dict with extracted_documents key containing list of ExtractedDocument objects

    Note:
        ID cards are typically short documents but contain critical
        information for verifying patient identity and insurance coverage.
    """
    llm = get_default_llm(temperature=0.0)
    structured_llm = llm.with_structured_output(IDCardSchema)

    target_docs = [doc for doc in state.classified_docs if doc.doc_type == DocumentType.ID_CARD]

    if not target_docs:
        log.info("⚠️ No ID cards found to process in this claim.")
        return {"extracted_documents": []}

    extracted_results: list[ExtractedDocument] = []

    for doc in target_docs:
        filename = doc.filename
        raw_text = doc.raw_text
        doc_type = doc.doc_type

        log.info(f"🪪  Extracting insurance details from: {filename}")

        try:
            truncated_text = raw_text[:5000]
            response: IDCardSchema = await structured_llm.ainvoke(
                [
                    SystemMessage(content=ID_CARD_EXTRACTION_SYSTEM_PROMPT),
                    HumanMessage(
                        content=(
                            f"Document Type: Insurance ID Card\n"
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
                f"✅ Extracted ID Card: {filename} | "
                f"Name: {response.full_name or 'N/A'} | "
                f"Policy #: {response.policy_number or 'N/A'} | "
                f"DOB: {response.date_of_birth or 'N/A'}"
            )

        except Exception as e:
            log.error(f"❌ ID Extraction Failed for {filename}: {e}")
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
