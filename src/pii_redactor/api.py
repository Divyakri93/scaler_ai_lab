import logging
import os
import shutil
import tempfile
from typing import Any, Dict, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

from pii_redactor.config import RedactorConfig
from pii_redactor.document.processor import RedactionPipeline
from pii_redactor.evaluation.evaluator import Evaluator

logger = logging.getLogger("pii_redactor_api")

app = FastAPI(
    title="PII Redactor API",
    description="REST API for redacting PII from DOCX files and evaluating performance.",
    version="0.1.0"
)

def cleanup_files(*filepaths: str) -> None:
    """
    Safely deletes temporary files from the system after sending the HTTP response.
    """
    for path in filepaths:
        try:
            if os.path.exists(path):
                os.remove(path)
                logger.debug(f"Cleaned up temporary file: {path}")
        except Exception as e:
            logger.warning(f"Failed to clean up temporary file {path}: {e}")

@app.get("/health")
def health_check() -> Dict[str, str]:
    """
    Liveness and readiness health check endpoint for Render/Kubernetes.
    """
    return {"status": "healthy"}

@app.post("/redact")
async def redact_docx(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    seed: Optional[int] = None,
    threshold: Optional[float] = None
) -> FileResponse:
    """
    Accepts a DOCX file upload, redacts PII, and returns the redacted DOCX.
    """
    if not file.filename.endswith(".docx"):
        raise HTTPException(
            status_code=400,
            detail="Unsupported file extension. Only .docx files are supported."
        )

    # Create safe temporary paths for processing
    fd_in, temp_in = tempfile.mkstemp(suffix=".docx")
    fd_out, temp_out = tempfile.mkstemp(suffix=".docx")
    os.close(fd_in)
    os.close(fd_out)

    try:
        # Save the uploaded file to disk
        with open(temp_in, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Configure redactor pipeline settings
        config = RedactorConfig()
        if seed is not None:
            config.seed = seed
        if threshold is not None:
            config.overall_threshold = threshold

        # Run the redaction
        pipeline = RedactionPipeline(config=config)
        pipeline.redact(temp_in, temp_out)

        # Register temp files for post-request deletion
        background_tasks.add_task(cleanup_files, temp_in, temp_out)

        # Return file response
        return FileResponse(
            path=temp_out,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=f"redacted_{file.filename}"
        )

    except Exception as e:
        # Clean up temp files immediately on error
        cleanup_files(temp_in, temp_out)
        logger.error(f"API redaction failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Redaction processing failed: {str(e)}"
        )

@app.post("/evaluate")
async def evaluate_docx(
    background_tasks: BackgroundTasks,
    docx_file: UploadFile = File(...),
    ground_truth_file: UploadFile = File(...)
) -> Dict[str, Any]:
    """
    Accepts a DOCX file and ground-truth JSON file, runs detection,
    and returns calculated Precision, Recall, F1 metrics.
    """
    if not docx_file.filename.endswith(".docx"):
        raise HTTPException(
            status_code=400,
            detail="docx_file must be a .docx file."
        )
    if not ground_truth_file.filename.endswith(".json"):
        raise HTTPException(
            status_code=400,
            detail="ground_truth_file must be a .json file."
        )

    # Create temporary files
    fd_docx, temp_docx = tempfile.mkstemp(suffix=".docx")
    fd_gt, temp_gt = tempfile.mkstemp(suffix=".json")
    fd_out, temp_out = tempfile.mkstemp(suffix=".docx")
    os.close(fd_docx)
    os.close(fd_gt)
    os.close(fd_out)

    try:
        # Save uploaded files
        with open(temp_docx, "wb") as buffer:
            shutil.copyfileobj(docx_file.file, buffer)
        with open(temp_gt, "wb") as buffer:
            shutil.copyfileobj(ground_truth_file.file, buffer)

        # Run pipeline with default seed (needed to populate detections dict)
        config = RedactorConfig(seed=42)
        pipeline = RedactionPipeline(config=config)
        redacted_entities = pipeline.redact(temp_docx, temp_out)

        # Execute evaluation
        evaluator = Evaluator(temp_gt)
        result = evaluator.evaluate(redacted_entities)

        # Register temp files for deletion
        background_tasks.add_task(cleanup_files, temp_docx, temp_gt, temp_out)
        
        # Convert response to dictionary (FastAPI will serialize automatically)
        return result.model_dump()

    except Exception as e:
        cleanup_files(temp_docx, temp_gt, temp_out)
        logger.error(f"API evaluation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Evaluation processing failed: {str(e)}"
        )
