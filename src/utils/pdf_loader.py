import base64

import fitz  # PyMuPDF
import pymupdf4llm
from langchain_core.messages import HumanMessage

from src.core.llm import get_default_llm
from src.utils.logger import log


def _perform_ai_ocr(doc: fitz.Document) -> str:
    """
    Perform OCR on a scanned PDF document using an AI LLM with vision capability.

    This function renders up to the first 5 pages of the given fitz.Document as PNG images
    (at 2x zoom for enhanced OCR accuracy), then sends them to an LLM supporting vision
    (e.g., Gemini-2.5-flash or GPT-4.1) for transcription.

    Args:
        doc (fitz.Document): The PDF document to OCR.

    Returns:
        str: Concatenated plain text (with basic markdown formatting if present), as transcribed
             by the vision LLM. If more than 5 pages, a note about truncation is appended.
    """
    full_text: list[str] = []
    llm = get_default_llm(temperature=0.0)

    log.info("👁️  Engaging AI Vision for OCR (Scanned Document detected)...")

    for i, page in enumerate[fitz.Page](doc):
        if i >= 5:
            full_text.append("\n...[Remaining pages truncated]...")
            break

        # Render Page to Image (PNG)
        pix: fitz.Pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img_bytes: bytes = pix.tobytes("png")
        img_base64 = base64.b64encode(img_bytes).decode("utf-8")

        msg = HumanMessage(
            content=[
                {
                    "type": "text",
                    "text": "Transcribe the text in this document page exactly as it appears. Preserve markdown formatting for tables and headers if possible.",
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{img_base64}"},
                },
            ]
        )

        try:
            response = llm.invoke([msg])
            full_text.append(f"--- PAGE {i+1} (OCR) ---\n{response.content}")
        except Exception as e:
            log.error(f"OCR Failed for page {i+1}: {e}")

    return "\n".join(full_text)


def extract_text_from_bytes(file_bytes: bytes, filename: str) -> str:
    """
    Extract text content from a PDF provided as bytes, auto-detecting the best extraction strategy.

    Extraction Workflow:
        1. Open PDF and check if it contains any pages.
        2. For the first page, check for available digital text.
            - If no/very little text, assume scanned image and invoke AI OCR fallback.
        3. Otherwise, attempt extraction to Markdown via PyMuPDF4LLM.
            - If extraction fails, logs warning and proceeds.
        4. If Markdown extraction is unsuccessful, fallback to extracting all raw text.
            - If still insufficient text, fallback again to AI OCR.
        5. Handles exceptions gracefully and returns empty string on unrecoverable error.

    Args:
        file_bytes (bytes): The PDF file content as bytes.
        filename (str): The filename (for logging and diagnostics only).

    Returns:
        str: The extracted text (markdown-formatted if possible, raw otherwise).
    """
    try:
        with fitz.open(stream=file_bytes, filetype="pdf") as doc:
            if doc.page_count == 0:
                log.warning(f"⚠️ Document is empty: {filename}")
                return ""

            # --- Check 1: Check If the pdf is a Scanned Image ---
            first_page_text = doc[0].get_text()
            is_scanned = len(first_page_text.strip()) < 50

            if is_scanned:
                log.warning(f"{filename} appears to be a scanned image. Switching to AI OCR.")
                return _perform_ai_ocr(doc)

            # --- Check 2: Try Standard Extraction ---
            try:
                md_text = pymupdf4llm.to_markdown(doc)
                return str(md_text)

            except Exception as e:
                log.warning(f"Markdown extraction failed: {e}")

            # --- Final Fallback: Try raw text or fallback to OCR ---
            raw_text = ""
            for page in doc:
                raw_text += page.get_text()

            if len(raw_text.strip()) < 50:
                ocr_result = _perform_ai_ocr(doc)
                return ocr_result

            return str(raw_text)

    except Exception as e:
        log.error(f"❌ Critical Error parsing {filename}: {e}")
        return ""
