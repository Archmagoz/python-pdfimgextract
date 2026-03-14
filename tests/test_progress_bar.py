from unittest.mock import patch, MagicMock

from pdfimgextract.progress_bar import (
    create_progress_bar,
    update_scan_stats,
    update_extract_stats,
    scanning_complete,
    finish_progress_bar,
    PROGRESS_BAR_WIDTH,
)


@patch("pdfimgextract.progress_bar.tqdm")
def test_create_progress_bar(mock_tqdm):
    """Verify tqdm initialization with standardized parameters."""
    create_progress_bar(total=10, desc="Test", unit="page")

    mock_tqdm.assert_called_once_with(
        total=10,
        desc="Test",
        colour="green",
        leave=True,
        ncols=PROGRESS_BAR_WIDTH,
        dynamic_ncols=False,
        unit=" page",
        smoothing=0.1,
    )


def test_update_scan_stats():
    """Verify postfix update for scanning phase."""
    mock_pb = MagicMock()
    update_scan_stats(mock_pb, unique=5, duplicates=2)
    mock_pb.set_postfix.assert_called_once_with(unique=5, dup=2)


def test_update_extract_stats():
    """Verify postfix update for extraction phase."""
    mock_pb = MagicMock()
    update_extract_stats(mock_pb, success=10, failed=1)
    mock_pb.set_postfix.assert_called_once_with(ok=10, fail=1)


def test_scanning_complete():
    """Verify description update and refresh on scan completion."""
    mock_pb = MagicMock()
    scanning_complete(mock_pb)
    mock_pb.set_description.assert_called_once_with("Scanning complete")
    mock_pb.refresh.assert_called_once()


def test_finish_progress_bar_success():
    """Branch: finish_progress_bar with cancelled=False."""
    mock_pb = MagicMock()
    finish_progress_bar(mock_pb, cancelled=False)

    mock_pb.set_description_str.assert_called_once_with("Extraction completed")
    assert mock_pb.colour == "green"
    mock_pb.refresh.assert_called_once()
    mock_pb.close.assert_called_once()


def test_finish_progress_bar_cancelled():
    """Branch: finish_progress_bar with cancelled=True."""
    mock_pb = MagicMock()
    finish_progress_bar(mock_pb, cancelled=True)

    mock_pb.set_description_str.assert_called_once_with("Cancelled (CTRL-C)")
    assert mock_pb.colour == "yellow"
    mock_pb.refresh.assert_called_once()
    mock_pb.close.assert_called_once()
