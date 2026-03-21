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

from pdfimgextract.datamodels import ExtractTask, ExtractResult
from pdfimgextract.filesystem import remove_file_safely


# ============================================================
# Result helpers
# ============================================================


def cancelled_result(task: ExtractTask) -> ExtractResult:
    """
    Create a result object representing a cancelled extraction task.

    Args:
        task (ExtractTask): Task that was cancelled.

    Returns:
        ExtractResult: Result marked as cancelled.
    """
    return ExtractResult(
        ok=False,
        cancelled=True,
        xref=task.xref,
        stem=task.stem,
        ext=None,
        temp_path=None,
        error="cancelled",
    )


def failure_result(task: ExtractTask, error: str) -> ExtractResult:
    """
    Create a result object representing a failed extraction task.

    Args:
        task (ExtractTask): Task that failed.
        error (str): Error message describing the failure.

    Returns:
        ExtractResult: Result marked as failed.
    """
    return ExtractResult(
        ok=False,
        cancelled=False,
        xref=task.xref,
        stem=task.stem,
        ext=None,
        temp_path=None,
        error=error,
    )


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
# Worker lifecycle
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

        if STOP_EVENT.is_set():
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
        if STOP_EVENT.is_set():
            return cancelled_result(task)

        # Temporary file used to ensure atomic writes
        temp_path = os.path.join(
            task.out_dir,
            f".pdfimgextract-tmp-{task.run_id}-{task.stem}.{ext}.part",
        )

        with open(temp_path, "wb") as f:
            f.write(image_bytes)

        # Remove partial file if cancellation happened during write
        if STOP_EVENT.is_set():
            remove_file_safely(temp_path)
            return cancelled_result(task)

        return ExtractResult(
            ok=True,
            cancelled=False,
            xref=task.xref,
            stem=task.stem,
            ext=ext,
            temp_path=temp_path,
            error=None,
        )

    except Exception as e:
        # Ensure temporary file is removed on failure
        remove_file_safely(temp_path)
        return failure_result(task, str(e))
