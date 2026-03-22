import pytest
import pdfimgextract.core.worker as worker
from unittest.mock import patch, MagicMock, mock_open
from pdfimgextract.core.worker import (
    init_worker,
    worker_extract,
    _close_worker_pdf,
    _cancelled_result,
    ExtractTask,
)


@pytest.fixture(autouse=True)
def reset_globals():
    """Hard reset of global state between every test to prevent leakage."""
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
    # Test the dedicated helper
    assert _cancelled_result(task).cancelled is True
    assert _cancelled_result(task).ok is False

    # Test the generic result helper directly
    res = worker._result(task, ok=True, ext="png", temp_path="tmp/path")
    assert res.ok is True
    assert res.ext == "png"
    assert res.temp_path == "tmp/path"


# --- Lifecycle ---
@patch("fitz.open")
@patch("atexit.register")
@patch("signal.signal")
def test_init_worker(mock_sig, mock_exit, mock_fitz):
    mock_event = MagicMock()  # Satisfies SharedEventProtocol
    init_worker("test.pdf", mock_event)

    assert worker.PDF_DOC is not None
    assert worker.STOP_EVENT == mock_event
    mock_sig.assert_called_once()
    mock_exit.assert_called_once_with(_close_worker_pdf)


def test__close_worker_pdf_logic():
    # Success path
    worker.PDF_DOC = MagicMock()
    _close_worker_pdf()
    assert worker.PDF_DOC is None

    # Exception path: Ensure it suppresses errors during PDF closure
    mock_doc = MagicMock()
    mock_doc.close.side_effect = Exception("Fitz cleanup failure")
    worker.PDF_DOC = mock_doc
    _close_worker_pdf()  # Should not raise
    assert worker.PDF_DOC is None


# --- Extraction Logic ---
def test_worker_uninitialized_guards():
    """Covers RuntimeError branches when init_worker wasn't called or failed."""
    task = create_task()

    # 1. No STOP_EVENT
    res = worker_extract(task)
    assert res.ok is False
    assert "stop event" in (res.error or "")

    # 2. No PDF_DOC (but event exists)
    worker.STOP_EVENT = MagicMock()
    worker.STOP_EVENT.is_set.return_value = False
    res = worker_extract(task)
    assert res.ok is False
    assert "PDF document" in (res.error or "")


def test_worker_data_validation_errors():
    """Covers cases where PyMuPDF returns malformed or empty data."""
    worker.STOP_EVENT = MagicMock(is_set=lambda: False)
    worker.PDF_DOC = MagicMock()
    task = create_task()

    # Case: Empty image data
    worker.PDF_DOC.extract_image.return_value = {"image": None, "ext": "png"}
    res = worker_extract(task)
    assert "empty image data" in (res.error or "")

    # Case: Empty/missing extension
    worker.PDF_DOC.extract_image.return_value = {"image": b"fake_data", "ext": ""}
    res = worker_extract(task)
    assert "empty file extension" in (res.error or "")


@patch("pdfimgextract.core.worker.remove_file_safely")
def test_worker_cancellation_checkpoints(mock_remove):
    """Verifies that the worker respects the STOP_EVENT at various stages."""
    worker.PDF_DOC = MagicMock()
    worker.PDF_DOC.extract_image.return_value = {"image": b"data", "ext": "png"}
    task = create_task()

    # Mock event to satisfy Protocol
    mock_event = MagicMock()
    worker.STOP_EVENT = mock_event

    # Point 1: Cancelled immediately
    mock_event.is_set.return_value = True
    assert worker_extract(task).cancelled is True

    # Point 2: Cancelled after extraction but before file write
    # is_set() is called: once at start, once before write
    mock_event.is_set.side_effect = [False, True]
    assert worker_extract(task).cancelled is True

    # Point 3: Cancelled after file write (Cleanup logic)
    # is_set() is called: start, before write, after write
    mock_event.is_set.side_effect = [False, False, True]
    with patch("builtins.open", mock_open()):
        res = worker_extract(task)
        assert res.cancelled is True
        # Verify it cleaned up the partial file
        mock_remove.assert_called()


@patch("pdfimgextract.core.worker.remove_file_safely")
def test_extraction_exception_cleanup(mock_remove):
    """Forces an exception during write to ensure temp_path is cleaned up."""
    worker.STOP_EVENT = MagicMock(is_set=lambda: False)
    worker.PDF_DOC = MagicMock()
    worker.PDF_DOC.extract_image.return_value = {"image": b"data", "ext": "png"}
    task = create_task()

    # Trigger exception during the 'with open' block
    with patch("builtins.open", side_effect=IOError("Disk Full")):
        res = worker_extract(task)

    assert res.ok is False
    assert "Disk Full" in (res.error or "")
    # Ensure cleanup was called because temp_path was already defined
    mock_remove.assert_called_once()


@patch("builtins.open", new_callable=mock_open)
def test_worker_extract_success(mock_file):
    """Standard success path."""
    worker.STOP_EVENT = MagicMock(is_set=lambda: False)
    worker.PDF_DOC = MagicMock()
    worker.PDF_DOC.extract_image.return_value = {
        "image": b"actual_bytes",
        "ext": "jpeg",
    }

    task = create_task()
    res = worker_extract(task)

    assert res.ok is True
    assert res.ext == "jpeg"
    assert ".part" in (res.temp_path or "")
    mock_file().write.assert_called_once_with(b"actual_bytes")
