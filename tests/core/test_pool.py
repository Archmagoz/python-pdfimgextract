import pytest

from unittest.mock import patch, MagicMock

from dataclasses import replace

from pdfimgextract.core.pool import run_pool, _handle_interrupt
from pdfimgextract.models.datamodels import Args, ExtractResult


class TestPool:
    """
    Test suite for the multiprocessing pool orchestration.
    Focuses on worker dispatch, result collection, and interrupt handling.
    """

    @pytest.fixture
    def mock_args(self):
        return Args(
            pdf_path="test.pdf", out_dir="out", workers=2, overwrite=False, dedup="xref"
        )

    @pytest.fixture
    def dummy_result(self):
        return ExtractResult(
            ok=True,
            cancelled=False,
            xref=1,
            stem="1",
            ext="png",
            temp_path="/tmp/1.tmp",
            error=None,
        )

    def test_handle_interrupt(self):
        """
        Verify that _handle_interrupt signals the event and terminates the pool.
        """
        mock_pool = MagicMock()
        mock_progress = MagicMock()
        mock_event = MagicMock()

        _handle_interrupt(mock_pool, mock_progress, mock_event)

        mock_event.set.assert_called_once()
        mock_progress.refresh.assert_called_once()
        assert "Cancelled" in mock_progress.set_description.call_args[0][0]
        mock_pool.terminate.assert_called_once()
        mock_pool.join.assert_called_once()

    @patch("pdfimgextract.core.pool.Pool")
    @patch("pdfimgextract.core.pool.finalize_result")
    def test_run_pool_success(
        self, mock_finalize, mock_pool_class, mock_args, dummy_result
    ):
        """
        Test the successful execution of the pool and result aggregation.
        """
        # Arrange
        mock_pool_instance = MagicMock()
        mock_pool_class.return_value = mock_pool_instance

        # Simulate imap_unordered returning our dummy result
        mock_pool_instance.imap_unordered.return_value = [dummy_result]

        # Mock finalize_result return: (updated_result, path)
        finalized = replace(dummy_result, temp_path=None)
        mock_finalize.return_value = (finalized, "out/1.png")

        mock_event = MagicMock()
        mock_event.is_set.return_value = False
        mock_progress = MagicMock()

        # Act
        results, failed, success, interrupted = run_pool(
            [MagicMock()], mock_args, mock_event, mock_progress
        )

        # Assert
        assert len(results) == 1
        assert success == 1
        assert len(failed) == 0
        assert interrupted is False
        mock_finalize.assert_called_once()
        mock_progress.update.assert_called_once_with(1)

    @patch("pdfimgextract.core.pool.Pool")
    @patch("pdfimgextract.core.pool.remove_file_safely")
    def test_run_pool_cancellation_logic(
        self, mock_remove, mock_pool_class, mock_args, dummy_result
    ):
        """
        Test the branch where stop_event is set during iteration.
        Ensures temporary files are removed and results are marked as cancelled.
        """
        mock_pool_instance = MagicMock()
        mock_pool_class.return_value = mock_pool_instance
        mock_pool_instance.imap_unordered.return_value = [dummy_result]

        mock_event = MagicMock()
        mock_event.is_set.return_value = True  # Simulate cancellation mid-run
        mock_progress = MagicMock()

        # Act
        results, failed, success, interrupted = run_pool(
            [MagicMock()], mock_args, mock_event, mock_progress
        )

        # Assert
        assert results[0].cancelled is True
        assert results[0].ok is False
        assert success == 0
        mock_remove.assert_called_once_with(dummy_result.temp_path)

    @patch("pdfimgextract.core.pool.Pool")
    @patch("pdfimgextract.core.pool._handle_interrupt")
    def test_run_pool_keyboard_interrupt(self, mock_handle, mock_pool_class, mock_args):
        """
        Test the try/except block for KeyboardInterrupt.
        """
        mock_pool_instance = MagicMock()
        mock_pool_class.return_value = mock_pool_instance
        # Force KeyboardInterrupt when iterating imap
        mock_pool_instance.imap_unordered.side_effect = KeyboardInterrupt()

        results, failed, success, interrupted = run_pool(
            [MagicMock()], mock_args, MagicMock(), MagicMock()
        )

        assert interrupted is True
        mock_handle.assert_called_once()

    @patch("pdfimgextract.core.pool.Pool")
    @patch("pdfimgextract.core.pool.finalize_result")
    def test_run_pool_tracking_failures(
        self, mock_finalize, mock_pool_class, mock_args, dummy_result
    ):
        """
        Ensure that results where ok=False but cancelled=False are added to the failed list.
        """
        mock_pool_instance = MagicMock()
        mock_pool_class.return_value = mock_pool_instance
        mock_pool_instance.imap_unordered.return_value = [dummy_result]

        # Mock a failure during finalization
        failed_res = replace(dummy_result, ok=False, error="IO Error", temp_path=None)
        mock_finalize.return_value = (failed_res, None)

        results, failed, success, interrupted = run_pool(
            [MagicMock()], mock_args, MagicMock(is_set=lambda: False), MagicMock()
        )

        assert success == 0
        assert len(failed) == 1
        assert failed[0].error == "IO Error"
