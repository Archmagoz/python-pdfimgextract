from unittest.mock import patch, MagicMock

from pdfimgextract.utils.progress_bar import (
    create_progress_bar,
    update_scan_stats,
    update_extract_stats,
    scanning_complete,
    finish_progress_bar,
)


class TestProgressBarUtils:
    """
    Test suite for progress bar configuration and state updates.
    Verifies that the UI remains consistent across different phases.
    """

    @patch("pdfimgextract.utils.progress_bar.tqdm")
    def test_create_progress_bar(self, mock_tqdm):
        """Verify the progress bar is initialized with correct styling."""
        create_progress_bar(total=100, desc="Testing", unit="img")

        mock_tqdm.assert_called_once()
        kwargs = mock_tqdm.call_args.kwargs

        assert kwargs["total"] == 100
        assert kwargs["desc"] == "Testing"
        assert kwargs["colour"] == "green"
        assert "img" in kwargs["unit"]

    def test_update_scan_stats(self):
        """Verify scanning stats (unique/dup) are passed to postfix."""
        mock_pb = MagicMock()
        update_scan_stats(mock_pb, unique=10, duplicates=5)
        mock_pb.set_postfix.assert_called_once_with(unique=10, dup=5)

    def test_update_extract_stats(self):
        """Verify extraction stats (ok/fail) are passed to postfix."""
        mock_pb = MagicMock()
        update_extract_stats(mock_pb, success=8, failed=2)
        mock_pb.set_postfix.assert_called_once_with(ok=8, fail=2)

    def test_scanning_complete(self):
        """Verify description update when scanning finishes."""
        mock_pb = MagicMock()
        scanning_complete(mock_pb)
        mock_pb.set_description.assert_called_once_with("Scanning complete")
        mock_pb.refresh.assert_called_once()

    def test_finish_progress_bar_success(self):
        """Verify visual state for normal completion."""
        mock_pb = MagicMock()
        finish_progress_bar(mock_pb, cancelled=False)

        mock_pb.set_description_str.assert_called_once_with("Extraction completed")
        assert mock_pb.colour == "green"
        mock_pb.close.assert_called_once()

    def test_finish_progress_bar_cancelled(self):
        """Verify visual state changes to yellow on cancellation."""
        mock_pb = MagicMock()
        finish_progress_bar(mock_pb, cancelled=True)

        mock_pb.set_description_str.assert_called_once_with("Cancelled (CTRL-C)")
        assert mock_pb.colour == "yellow"
        mock_pb.refresh.assert_called_once()
        mock_pb.close.assert_called_once()
