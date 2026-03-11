import fitz
import atexit
import os
import signal

from typing import Protocol
from contextlib import suppress

from .cleanup import remove_file_safely
from .datamodels import ExtractTask, ExtractResult

# ============================================================
# Result helpers
# ============================================================


def cancelled_result(task: ExtractTask) -> ExtractResult:
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
    def is_set(self) -> bool: ...
    def set(self) -> None: ...


PDF_DOC: fitz.Document | None = None
STOP_EVENT: SharedEventProtocol | None = None


# ============================================================
# Worker lifecycle
# ============================================================


def close_worker_pdf() -> None:
    global PDF_DOC
    if PDF_DOC is not None:
        with suppress(Exception):
            PDF_DOC.close()
        PDF_DOC = None


def init_worker(pdf_path: str, stop_event: SharedEventProtocol) -> None:
    global PDF_DOC, STOP_EVENT

    signal.signal(signal.SIGINT, signal.SIG_IGN)

    PDF_DOC = fitz.open(pdf_path)
    STOP_EVENT = stop_event

    atexit.register(close_worker_pdf)


# ============================================================
# Worker extraction
# ============================================================


def worker_extract(task: ExtractTask) -> ExtractResult:
    global PDF_DOC, STOP_EVENT

    temp_path: str | None = None

    try:
        if STOP_EVENT is None:
            raise RuntimeError("Worker stop event is not initialized.")

        if STOP_EVENT.is_set():
            return cancelled_result(task)

        if PDF_DOC is None:
            raise RuntimeError("Worker PDF document is not initialized.")

        base_image = PDF_DOC.extract_image(task.xref)

        image_bytes = base_image.get("image")
        raw_ext = str(base_image.get("ext", "")).strip()

        if not image_bytes:
            raise RuntimeError("PDF image extraction returned empty image data.")

        if not raw_ext:
            raise RuntimeError("PDF image extraction returned empty file extension.")

        ext = raw_ext.lower()

        if STOP_EVENT.is_set():
            return cancelled_result(task)

        temp_path = os.path.join(
            task.out_dir,
            f".pdfimgextract-tmp-{task.run_id}-{task.stem}.{ext}.part",
        )

        with open(temp_path, "wb") as f:
            f.write(image_bytes)

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
        remove_file_safely(temp_path)
        return failure_result(task, str(e))
