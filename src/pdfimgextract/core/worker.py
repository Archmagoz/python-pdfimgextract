"""
Worker process responsible for extracting images from a PDF.

Each worker keeps its own open PDF document instance and processes
tasks independently. Extraction writes to temporary files to ensure
atomic output and safe cancellation.
"""

import fitz
import atexit
import os
import signal

from contextlib import suppress

from pdfimgextract.models.types import ExtractTask, ExtractResult, SharedEventProtocol
from pdfimgextract.utils.filesystem import remove_file_safely

# ============================================================
# Worker global state
# ============================================================


# Per-process state (initialized once per worker)
PDF_DOC: fitz.Document | None = None
STOP_EVENT: SharedEventProtocol | None = None


# ============================================================
# Result helpers
# ============================================================


def _result(
    task: ExtractTask,
    *,
    ok: bool,
    cancelled: bool = False,
    temp_path: str | None = None,
    error: str | None = None,
) -> ExtractResult:
    """
    Build a normalized ExtractResult from a task.
    """

    return ExtractResult(
        ok=ok,
        cancelled=cancelled,
        xref=task.xref,
        filename=task.filename,
        temp_path=temp_path,
        error=error,
    )


def _cancelled_result(task: ExtractTask) -> ExtractResult:
    """
    Shortcut for a cancelled task result.
    """
    return _result(task, ok=False, cancelled=True, error="cancelled")


# ============================================================
# Worker lifecycle
# ============================================================


def init_worker(pdf_path: str, stop_event: SharedEventProtocol) -> None:
    """
    Initialize per-worker state.

    Each worker:
    - opens its own PDF document
    - receives a shared stop event
    - ignores SIGINT (handled by parent)
    """

    global PDF_DOC, STOP_EVENT

    # Prevent workers from handling CTRL+C directly
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    PDF_DOC = fitz.open(pdf_path)
    STOP_EVENT = stop_event

    # Ensure cleanup on process exit
    atexit.register(_close_worker_pdf)


# ============================================================
# Utils
# ============================================================


def _close_worker_pdf() -> None:
    """
    Close the worker's PDF document on process exit.
    """

    global PDF_DOC
    if PDF_DOC is not None:
        with suppress(Exception):
            PDF_DOC.close()
        PDF_DOC = None


def _is_cancelled() -> bool:
    """
    Check whether a global cancellation signal was triggered.
    """
    return STOP_EVENT is not None and STOP_EVENT.is_set()


# ============================================================
# Worker extraction
# ============================================================


def worker_extract(task: ExtractTask) -> ExtractResult:
    """
    Extract a single image and write it to a temporary file.

    Returns a result describing success, failure, or cancellation.
    """

    global PDF_DOC, STOP_EVENT

    temp_path: str | None = None

    try:
        # Validate worker state
        if STOP_EVENT is None:
            raise RuntimeError("Worker stop event is not initialized.")

        if PDF_DOC is None:
            raise RuntimeError("Worker PDF document is not initialized.")

        # Early cancellation check
        if _is_cancelled():
            return _cancelled_result(task)

        # Extract raw image data from PDF
        base_image = PDF_DOC.extract_image(task.xref)

        image_bytes = base_image.get("image")

        if not image_bytes:
            raise RuntimeError("PDF image extraction returned empty image data.")

        # Check again before performing disk I/O
        if _is_cancelled():
            return _cancelled_result(task)

        # Write to temp file (ensures atomic commit later)
        temp_path = os.path.join(
            task.out_dir,
            f".pdfimgextract-tmp-{task.filename}.part",
        )

        with open(temp_path, "wb") as f:
            f.write(image_bytes)

        # Handle cancellation during write
        if _is_cancelled():
            remove_file_safely(temp_path)
            return _cancelled_result(task)

        return _result(task, ok=True, temp_path=temp_path)

    except Exception as e:
        # Cleanup temp file on any failure
        remove_file_safely(temp_path)

        return _result(task, ok=False, error=str(e))
