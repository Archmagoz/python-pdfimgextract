import pytest

from unittest.mock import patch, MagicMock, mock_open

from pdfimgextract.core import worker
from pdfimgextract.models.datamodels import ExtractTask


class TestWorker:
    """
    Finalized test suite for worker.py hitting 100% coverage.
    Uses explicit type guards to satisfy static analysis.
    """

    @pytest.fixture(autouse=True)
    def reset_worker_globals(self):
        worker.PDF_DOC = None
        worker.STOP_EVENT = None
        yield
        worker.PDF_DOC = None
        worker.STOP_EVENT = None

    @pytest.fixture
    def mock_task(self):
        return ExtractTask(xref=100, stem="001", out_dir="out", run_id="test")

    # --- Lifecycle ---

    @patch("pdfimgextract.core.worker.fitz.open")
    @patch("pdfimgextract.core.worker.signal.signal")
    @patch("pdfimgextract.core.worker.atexit.register")
    def test_init_worker(self, mock_atexit, mock_signal, mock_fitz_open):
        mock_event = MagicMock()
        worker.init_worker("dummy.pdf", mock_event)
        assert worker.STOP_EVENT == mock_event
        mock_fitz_open.assert_called_once()

    def test_close_worker_pdf_suppress(self):
        """Covers the suppress(Exception) in close_worker_pdf."""
        mock_doc = MagicMock()
        mock_doc.close.side_effect = Exception("Fitz Error")
        worker.PDF_DOC = mock_doc
        worker.close_worker_pdf()
        assert worker.PDF_DOC is None

    # --- Extraction Cancellation & Logic ---

    def test_worker_extract_cancelled_at_start(self, mock_task):
        worker.PDF_DOC = MagicMock()
        mock_event = MagicMock()
        mock_event.is_set.return_value = True
        worker.STOP_EVENT = mock_event

        res = worker.worker_extract(mock_task)
        assert res.cancelled is True

    @patch("pdfimgextract.core.worker.remove_file_safely")
    def test_worker_extract_cancelled_before_io(self, mock_remove, mock_task):
        mock_doc = MagicMock()
        mock_doc.extract_image.return_value = {"image": b"data", "ext": "png"}
        worker.PDF_DOC = mock_doc

        mock_event = MagicMock()
        mock_event.is_set.side_effect = [False, True]
        worker.STOP_EVENT = mock_event

        res = worker.worker_extract(mock_task)
        assert res.cancelled is True

    @patch("pdfimgextract.core.worker.open", new_callable=mock_open)
    @patch("pdfimgextract.core.worker.remove_file_safely")
    def test_worker_extract_cancelled_after_io(self, mock_remove, mock_file, mock_task):
        mock_doc = MagicMock()
        mock_doc.extract_image.return_value = {"image": b"data", "ext": "png"}
        worker.PDF_DOC = mock_doc

        mock_event = MagicMock()
        mock_event.is_set.side_effect = [False, False, True]
        worker.STOP_EVENT = mock_event

        res = worker.worker_extract(mock_task)
        assert res.cancelled is True
        mock_remove.assert_called_once()

    def test_worker_extract_doc_is_none(self, mock_task):
        worker.STOP_EVENT = MagicMock(is_set=lambda: False)
        res = worker.worker_extract(mock_task)

        assert res.error is not None  # <--- TYPE GUARD
        assert "document is not initialized" in res.error

    def test_worker_extract_event_is_none(self, mock_task):
        """Covers STOP_EVENT is None branch."""
        res = worker.worker_extract(mock_task)
        assert res.error is not None  # <--- TYPE GUARD
        assert "stop event is not initialized" in res.error

    @patch("pdfimgextract.core.worker.remove_file_safely")
    def test_worker_extract_invalid_ext(self, mock_remove, mock_task):
        mock_doc = MagicMock()
        mock_doc.extract_image.return_value = {"image": b"data", "ext": ""}
        worker.PDF_DOC = mock_doc
        worker.STOP_EVENT = MagicMock(is_set=lambda: False)

        res = worker.worker_extract(mock_task)
        assert res.error is not None  # <--- TYPE GUARD
        assert "empty file extension" in res.error

    @patch("pdfimgextract.core.worker.remove_file_safely")
    def test_worker_extract_no_bytes(self, mock_remove, mock_task):
        """Covers image_bytes is None branch."""
        mock_doc = MagicMock()
        mock_doc.extract_image.return_value = {"image": None, "ext": "jpg"}
        worker.PDF_DOC = mock_doc
        worker.STOP_EVENT = MagicMock(is_set=lambda: False)

        res = worker.worker_extract(mock_task)
        assert res.error is not None  # <--- TYPE GUARD
        assert "empty image data" in res.error

    @patch("pdfimgextract.core.worker.open", new_callable=mock_open)
    def test_worker_extract_success(self, mock_file, mock_task):
        mock_doc = MagicMock()
        mock_doc.extract_image.return_value = {"image": b"data", "ext": "png"}
        worker.PDF_DOC = mock_doc
        worker.STOP_EVENT = MagicMock(is_set=lambda: False)

        res = worker.worker_extract(mock_task)
        assert res.ok is True
        assert res.temp_path is not None  # <--- TYPE GUARD
        assert ".part" in res.temp_path
