"""
Worker process responsible for extracting images from a PDF.

Each worker keeps its own open PDF document instance and processes
extraction tasks in parallel. Extraction writes to temporary files
to ensure atomic output and safe cancellation.
"""

import fitz
import atexit
import os
import signal

from typing import Protocol
from contextlib import suppress

from pdfimgextract.models.datamodels import ExtractTask, ExtractResult
from pdfimgextract.utils.filesystem import remove_file_safely


# ============================================================
# Result helpers
# ============================================================


def result(
    task: ExtractTask,
    *,
    ok: bool,
    cancelled: bool = False,
    ext: str | None = None,
    temp_path: str | None = None,
    error: str | None = None,
) -> ExtractResult:
    """
    Generic helper to create an ExtractResult.

    Args:
        task (ExtractTask): Task associated with the result.
        ok (bool): Whether the operation succeeded.
        cancelled (bool, optional): Whether the task was cancelled.
        ext (str | None, optional): File extension.
        temp_path (str | None, optional): Temporary file path.
        error (str | None, optional): Error message.

    Returns:
        ExtractResult: Result object.
    """
    return ExtractResult(
        ok=ok,
        cancelled=cancelled,
        xref=task.xref,
        stem=task.stem,
        ext=ext,
        temp_path=temp_path,
        error=error,
    )


def cancelled_result(task: ExtractTask) -> ExtractResult:
    return result(task, ok=False, cancelled=True, error="cancelled")


# ============================================================
# Worker global state
# ============================================================


class SharedEventProtocol(Protocol):
    """
    Protocol defining the minimal interface required for a shared stop event.

    Used to allow compatibility with multiprocessing.Event without importing
    the concrete implementation in this module.
    """

    def is_set(self) -> bool: ...
    def set(self) -> None: ...


# Shared worker state
PDF_DOC: fitz.Document | None = None
STOP_EVENT: SharedEventProtocol | None = None

# ============================================================
# Utils
# ============================================================


def close_worker_pdf() -> None:
    """
    Close the PDF document held by the worker process.

    This function is registered with `atexit` to ensure that the
    document is always closed when the worker exits.
    """
    global PDF_DOC
    if PDF_DOC is not None:
        with suppress(Exception):
            PDF_DOC.close()
        PDF_DOC = None


def is_cancelled() -> bool:
    return STOP_EVENT is not None and STOP_EVENT.is_set()


# ============================================================
# Worker lifecycle
# ============================================================


def init_worker(pdf_path: str, stop_event: SharedEventProtocol) -> None:
    """
    Initialize worker process state.

    Each worker opens its own PDF document instance and receives a
    shared stop event used to coordinate cancellation.

    SIGINT is ignored so the parent process can handle interrupts.

    Args:
        pdf_path (str): Path to the PDF file.
        stop_event (SharedEventProtocol): Shared event used to signal cancellation.
    """
    global PDF_DOC, STOP_EVENT

    # Ignore CTRL-C in worker processes (handled by the parent)
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    PDF_DOC = fitz.open(pdf_path)
    STOP_EVENT = stop_event

    # Ensure the PDF is closed when the worker exits
    atexit.register(close_worker_pdf)


# ============================================================
# Worker extraction
# ============================================================


def worker_extract(task: ExtractTask) -> ExtractResult:
    """
    Extract a single image from the PDF.

    The worker retrieves the image using its xref identifier,
    writes it to a temporary file, and returns a result describing
    the outcome of the extraction.

    The function periodically checks the shared stop event so the
    extraction pipeline can cancel quickly if requested.

    Args:
        task (ExtractTask): Extraction task containing image metadata.

    Returns:
        ExtractResult: Result of the extraction attempt.
    """
    global PDF_DOC, STOP_EVENT

    temp_path: str | None = None

    try:
        if STOP_EVENT is None:
            raise RuntimeError("Worker stop event is not initialized.")

        if is_cancelled():
            return cancelled_result(task)

        if PDF_DOC is None:
            raise RuntimeError("Worker PDF document is not initialized.")

        # Extract image data from the PDF using the xref identifier
        base_image = PDF_DOC.extract_image(task.xref)

        image_bytes = base_image.get("image")
        raw_ext = str(base_image.get("ext", "")).strip()

        if not image_bytes:
            raise RuntimeError("PDF image extraction returned empty image data.")

        if not raw_ext:
            raise RuntimeError("PDF image extraction returned empty file extension.")

        ext = raw_ext.lower()

        # Check again for cancellation before writing to disk
        if is_cancelled():
            return cancelled_result(task)

        # Temporary file used to ensure atomic writes
        temp_path = os.path.join(
            task.out_dir,
            f".pdfimgextract-tmp-{task.run_id}-{task.stem}.{ext}.part",
        )

        with open(temp_path, "wb") as f:
            f.write(image_bytes)

        # Remove partial file if cancellation happened during write
        if is_cancelled():
            remove_file_safely(temp_path)
            return cancelled_result(task)

        return result(task, ok=True, ext=ext, temp_path=temp_path)

    except Exception as e:
        # Ensure temporary file is removed on failure
        remove_file_safely(temp_path)
        return result(task, ok=False, error=str(e))
