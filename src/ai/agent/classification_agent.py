"""
Classification Agent Node
Determines document types from raw text using LLM
"""

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from src.ai.graph.state import ClaimState, ClassificationSchema, ClassifiedDocument
from src.ai.prompts import CLASSIFICATION_SYSTEM_PROMPT
from src.core.llm import get_default_llm
from src.schema.enum import DocumentType
from src.utils.logger import log


async def classification_node(state: ClaimState, config: RunnableConfig) -> dict[str, Any]:
    """
    LangGraph Node: Classification Agent.

    Takes the raw text from the state, sends it to the LLM to determine
    the document type, and updates the state with the classification result.

    Args:
        state: Current claim processing state
        config: LangGraph runtime configuration

    Returns:
        Dict with classified_docs key containing list of classified documents
    """
    llm = get_default_llm(temperature=0.0)
    structured_llm = llm.with_structured_output(ClassificationSchema)

    classified_docs: list[ClassifiedDocument] = []

    for doc_input in state.inputs:
        filename = doc_input.filename
        raw_text = doc_input.raw_text

        if not raw_text or len(raw_text.strip()) < 10:
            log.warning(f"⚠️ Text for {filename} is too short. Classifying as 'other'.")
            classified_docs.append(
                ClassifiedDocument(
                    filename=filename,
                    doc_type=DocumentType.OTHER,
                    reasoning="Insufficient text content extracted.",
                    confidence=0.0,
                    raw_text=raw_text,
                )
            )
            continue

        try:
            truncated_text = raw_text[:10000]
            response: ClassificationSchema = await structured_llm.ainvoke(
                [
                    SystemMessage(content=CLASSIFICATION_SYSTEM_PROMPT),
                    HumanMessage(
                        content=f"Document Filename: {filename}\n\nDocument Content:\n{truncated_text}"
                    ),
                ],
                config=config,
            )

            log.info(
                f"🧾 Classified {filename} -> {response.doc_type.value} "
                f"(confidence: {response.confidence:.2%})"
            )

            classified_docs.append(
                ClassifiedDocument(
                    filename=filename,
                    doc_type=response.doc_type,
                    reasoning=response.reasoning,
                    confidence=response.confidence,
                    raw_text=raw_text,
                )
            )

        except Exception as e:
            log.error(f"❌ Error classifying {filename}: {e}")
            classified_docs.append(
                ClassifiedDocument(
                    filename=filename,
                    doc_type=DocumentType.OTHER,
                    reasoning=f"Classification failed: {e!s}",
                    confidence=0.0,
                    raw_text=raw_text,
                )
            )

    return {"classified_docs": classified_docs}
