import pytest

from unittest.mock import patch, MagicMock, mock_open

# Access the module directly to force-reset global variables
import pdfimgextract.core.worker as worker
from pdfimgextract.core.worker import (
    init_worker,
    worker_extract,
    close_worker_pdf,
    cancelled_result,
    failure_result,
    ExtractTask,
)


@pytest.fixture(autouse=True)
def reset_globals():
    """Hard reset of global state between every test."""
    worker.PDF_DOC = None
    worker.STOP_EVENT = None
    yield
    worker.PDF_DOC = None
    worker.STOP_EVENT = None


def create_task():
    return ExtractTask(xref=10, stem="01", out_dir="out", run_id="test")


# --- Result Helpers ---
def test_result_helpers():
    task = create_task()
    assert cancelled_result(task).cancelled is True
    assert failure_result(task, "err").ok is False


# --- Lifecycle ---
@patch("fitz.open")
@patch("atexit.register")
@patch("signal.signal")
def test_init_worker(mock_sig, mock_exit, mock_fitz):
    init_worker("test.pdf", MagicMock())
    assert worker.PDF_DOC is not None
    mock_sig.assert_called_once()


def test_close_worker_pdf_logic():
    # Success path
    worker.PDF_DOC = MagicMock()
    close_worker_pdf()
    assert worker.PDF_DOC is None

    # Line 165: Exception path (suppress)
    mock_doc = MagicMock()
    mock_doc.close.side_effect = Exception("fail")
    worker.PDF_DOC = mock_doc
    close_worker_pdf()  # Should not raise
    assert worker.PDF_DOC is None


# --- Extraction Logic ---
def test_worker_guards():
    """Covers RuntimeError branches for uninitialized state."""
    task = create_task()

    # 1. No STOP_EVENT
    res = worker_extract(task)
    assert res.ok is False
    assert res.error is not None  # Type guard for the linter
    assert "stop event" in res.error

    # 2. No PDF_DOC
    import pdfimgextract.core.worker as worker

    worker.STOP_EVENT = MagicMock(is_set=lambda: False)
    res = worker_extract(task)
    assert res.ok is False
    assert res.error is not None  # Type guard for the linter
    assert "PDF document" in res.error


def test_worker_data_validation():
    """Covers empty data and extension RuntimeErrors with type guards."""
    worker.STOP_EVENT = MagicMock(is_set=lambda: False)
    worker.PDF_DOC = MagicMock()
    task = create_task()

    # 1. Empty image data
    worker.PDF_DOC.extract_image.return_value = {"image": None, "ext": "png"}
    res_data = worker_extract(task)
    assert res_data.error is not None  # <--- Type Guard
    assert "empty image data" in res_data.error

    # 2. Empty extension
    worker.PDF_DOC.extract_image.return_value = {"image": b"...", "ext": ""}
    res_ext = worker_extract(task)
    assert res_ext.error is not None  # <--- Type Guard
    assert "empty file extension" in res_ext.error


@patch("pdfimgextract.core.worker.remove_file_safely")
def test_worker_cancellation_logic(mock_remove):
    worker.STOP_EVENT = MagicMock()
    worker.PDF_DOC = MagicMock()
    worker.PDF_DOC.extract_image.return_value = {"image": b"d", "ext": "png"}
    task = create_task()

    # Point 1: Before extraction
    worker.STOP_EVENT.is_set.return_value = True
    assert worker_extract(task).cancelled is True

    # Point 2: Before write
    worker.STOP_EVENT.is_set.side_effect = [False, True]
    assert worker_extract(task).cancelled is True

    # Point 3: After write (Line 186 cleanup)
    worker.STOP_EVENT.is_set.side_effect = [False, False, True]
    with patch("builtins.open", mock_open()):
        res = worker_extract(task)
        assert res.cancelled is True
        mock_remove.assert_called()


# --- THE KILLER TEST FOR LINE 186 ---
@patch("pdfimgextract.core.worker.remove_file_safely")
def test_coverage_line_186_catch_all(mock_remove):
    """
    Forces Line 186 by ensuring temp_path is set, then crashing.
    """
    worker.STOP_EVENT = MagicMock(is_set=lambda: False)
    worker.PDF_DOC = MagicMock()
    # Return valid dictionary so we pass lines 167-171
    worker.PDF_DOC.extract_image.return_value = {"image": b"data", "ext": "png"}

    task = create_task()

    # Crash at open() -> Line 180.
    # Because Line 175 (temp_path assignment) already finished, 186 MUST run.
    with patch("builtins.open", side_effect=RuntimeError("Force Line 186")):
        res = worker_extract(task)

    assert res.ok is False
    assert res.error is not None
    assert "Force Line 186" in res.error
    mock_remove.assert_called_once()


@patch("builtins.open", mock_open())
def test_worker_extract_success():
    worker.STOP_EVENT = MagicMock(is_set=lambda: False)
    worker.PDF_DOC = MagicMock()
    worker.PDF_DOC.extract_image.return_value = {"image": b"data", "ext": "png"}
    res = worker_extract(create_task())
    assert res.ok is True
    assert res.temp_path is not None
