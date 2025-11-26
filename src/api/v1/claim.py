import gc
import uuid

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile, status
from fastapi.concurrency import run_in_threadpool

from src.ai.graph import claim_graph_app
from src.ai.graph.state import DocumentInput
from src.schema.claim_dto import (
    ClaimDecision,
    ClaimProcessResponse,
    ValidationReport,
    ValidationResponse,
)
from src.service.s3_service import s3_service
from src.utils.logger import log
from src.utils.pdf_loader import extract_text_from_bytes

router = APIRouter()

# --- CONSTANTS FOR FREE TIER PROTECTION ---
MAX_BATCH_SIZE = 3
MAX_FILE_SIZE_MB = 5
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


def background_s3_upload(file_bytes: bytes, filename: str, claim_id: str) -> None:
    """
    Asynchronously uploads the given file to S3 storage in a background thread.
    Non-blocking: Ensures API responsiveness for large files.
    """
    try:
        s3_key = s3_service.upload_file_sync(file_bytes, f"{claim_id}_{filename}")
        log.info(f"✅ Background Upload Success: {filename} -> {s3_key}")

        # TODO: Store the file record in PostgreSQL for later retrieval

    except Exception as e:
        log.error(f"❌ Background Upload Failed for {filename}: {e}")


@router.post(
    "/process-claim",
    status_code=status.HTTP_200_OK,
    response_model=ClaimProcessResponse,
    summary="Process Claim PDFs for AI Extraction & Validation",
    responses={
        200: {
            "description": "Claim processed successfully. Extraction and validation results provided.",
            "model": ClaimProcessResponse,
        },
        422: {
            "description": "Unprocessable Entity. No valid text could be extracted from the uploaded files.",
            "content": {
                "application/json": {"example": {"detail": "An unexpected error occurred"}}
            },
        },
        500: {
            "description": "Internal server error during claim processing.",
            "content": {
                "application/json": {"example": {"detail": "An unexpected error occurred"}}
            },
        },
    },
)
async def process_claim(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),  # noqa: B008
) -> ClaimProcessResponse:
    """
    This endpoint allows you to submit one or more PDF files (e.g., bills, ID cards, discharge summaries)
    as part of a single insurance claim process.

    **Ingestion/Validation Pipeline:**
    - Performs text extraction with fallback to AI-powered OCR for scanned documents.
    - Each file's contents are parsed into structured data according to their detected type.
    - Runs an LLM-driven validation workflow to check for completeness, consistency, and possible fraud.
    - Returns the final validation report, extracted structured data, and a list of successfully
    processed files.

    **Resource Protections:**
    - Maximum file size: 5MB per file; excessively large uploads are skipped (not errored).
    - All files are uploaded in the background to S3 for safekeeping.

    **Returns:**
    - `HTTP 200:` On success, returns the claim ID, extracted data/results, and validation report.

    **Raises:**
    - `HTTP 422:` If no files yielded valid extractable text.
    - `HTTP 500:` Internal server errors.
    """
    claim_id = str(uuid.uuid4())
    graph_inputs: list[DocumentInput] = []
    uploaded_files_metadata: list[str] = []

    log.info(f"🚀 Processing Claim {claim_id} with {len(files)} files...")

    for file in files:
        filename = file.filename or "unknown.pdf"

        # Protection: Check Content-Length (explicit size checking)
        if file.size and file.size > MAX_FILE_SIZE_BYTES:
            log.warning(f"Skipping {filename}: exceeds {MAX_FILE_SIZE_MB}MB limit")
            continue

        try:
            file_bytes = await file.read()

            if not file_bytes:
                log.warning(f"Skipping empty file: {filename}")
                continue

            # Schedule S3 Upload (Background)
            background_tasks.add_task(background_s3_upload, file_bytes, filename, claim_id)

            # Optimization: Run CPU-Heavy Extraction in ThreadPool
            extracted_text = await run_in_threadpool(extract_text_from_bytes, file_bytes, filename)

            # Memory Optimization: Explicitly delete bytes reference
            del file_bytes
            gc.collect()

            if not extracted_text:
                log.warning(
                    f"Could not extract text from {filename}. It might be empty, encrypted, or corrupted."
                )
                continue

            graph_inputs.append(
                DocumentInput(
                    claim_id=claim_id,
                    filename=filename,
                    raw_text=extracted_text,
                    file_size=file.size,
                ),
            )
            uploaded_files_metadata.append(filename)

        except Exception as e:
            log.error(f"Error processing file {filename}: {e}")
            continue

    if not graph_inputs:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="No valid text could be extracted from any of the uploaded files.",
        )

    # 5. Run AI Graph (Batch)
    workflow_input = {"inputs": graph_inputs}

    try:
        result = await claim_graph_app.ainvoke(input=workflow_input, print_mode=["updates"])
        validation_report: ValidationReport = result.get("validation_report")

        return ClaimProcessResponse(
            documents=uploaded_files_metadata,
            validation=ValidationResponse(
                missing_documents=validation_report.missing_documents,
                discrepancies=validation_report.discrepancies,
                validation_timestamp=validation_report.validation_timestamp,
            ),
            claim_decision=ClaimDecision(
                status=validation_report.status, reason=validation_report.reason
            ),
        )

    except Exception as e:
        log.error(f"AI Workflow Failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"AI processing failed: {e!s}"
        ) from e
