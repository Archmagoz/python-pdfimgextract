import pytest

from unittest.mock import MagicMock, patch
from pdfimgextract.extract import extract_images_parallel
from pdfimgextract.exit_codes import EXIT_SUCCESS, EXIT_FAILURE
from pdfimgextract.datamodels import Args

# --- Fixtures ---


@pytest.fixture
def mock_args():
    return Args(
        pdf_path="test.pdf", out_dir="out_dir", workers=4, overwrite=False, dedup="xref"
    )


# --- Success Paths ---


@patch("pdfimgextract.extract.build_tasks")
def test_extract_no_images_found(mock_build, mock_args, capsys):
    """Test branch where build_tasks returns an empty list."""
    mock_build.return_value = []

    result = extract_images_parallel(mock_args)

    assert result == EXIT_SUCCESS
    captured = capsys.readouterr()
    assert "No images found" in captured.out


@patch("pdfimgextract.extract.build_tasks")
@patch("pdfimgextract.extract.create_progress_bar")
@patch("pdfimgextract.extract.run_pool")
@patch("pdfimgextract.extract.print_summary")
@patch("pdfimgextract.extract.os.makedirs")
@patch("pdfimgextract.extract.cleanup_stale_temp_files")
def test_extract_full_success(
    mock_cleanup,
    mock_mkdir,
    mock_summary,
    mock_pool,
    mock_progress,
    mock_build,
    mock_args,
):
    """Test the normal 'else' completion path with 0 failures."""
    mock_build.return_value = [MagicMock()]  # 1 task
    mock_pool.return_value = (
        [],
        [],
        1,
        False,
    )  # results, failed, success_count, interrupted

    # Mock summary to indicate no errors
    mock_summary_obj = MagicMock()
    mock_summary_obj.interrupted = False
    mock_summary_obj.failed = 0
    mock_summary.return_value = mock_summary_obj

    result = extract_images_parallel(mock_args)

    assert result == EXIT_SUCCESS
    mock_cleanup.assert_called_once()
    mock_mkdir.assert_called_with(mock_args.out_dir, exist_ok=True)


# --- Error & Exception Branches ---


@patch("pdfimgextract.extract.build_tasks")
@patch("pdfimgextract.extract.run_pool")
def test_extract_keyboard_interrupt(mock_pool, mock_build, mock_args, capsys):
    """Test KeyboardInterrupt handling during pool execution."""
    mock_build.return_value = [MagicMock()]
    mock_pool.side_effect = KeyboardInterrupt()

    with patch("pdfimgextract.extract.cleanup_stale_temp_files") as mock_cleanup:
        result = extract_images_parallel(mock_args)

    assert result == EXIT_FAILURE
    mock_cleanup.assert_called_once()
    captured = capsys.readouterr()
    assert "interrupted by user" in captured.err


@patch("pdfimgextract.extract.build_tasks")
def test_extract_fatal_exception(mock_build, mock_args, capsys):
    """Test the general 'except Exception' branch."""
    mock_build.side_effect = RuntimeError("Something went wrong")

    result = extract_images_parallel(mock_args)

    assert result == EXIT_FAILURE
    captured = capsys.readouterr()
    assert "Fatal error: Something went wrong" in captured.err


@patch("pdfimgextract.extract.build_tasks")
@patch("pdfimgextract.extract.run_pool")
@patch("pdfimgextract.extract.print_summary")
def test_extract_failure_due_to_failed_tasks(
    mock_summary, mock_pool, mock_build, mock_args
):
    """Test branch where extraction completes but some tasks failed."""
    mock_build.return_value = [MagicMock()]
    mock_pool.return_value = ([], ["error_log"], 0, False)

    mock_summary_obj = MagicMock()
    mock_summary_obj.interrupted = False
    mock_summary_obj.failed = 1
    mock_summary.return_value = mock_summary_obj

    result = extract_images_parallel(mock_args)

    assert result == EXIT_FAILURE


# --- Edge Cases for 100% Coverage ---


@patch("pdfimgextract.extract.build_tasks")
@patch("pdfimgextract.extract.create_progress_bar")
@patch("pdfimgextract.extract.finish_progress_bar")
def test_finish_bar_exception_suppression(mock_finish, mock_pb, mock_build, mock_args):
    """
    Cover the 'with suppress(Exception)' block inside finish_progress_bar calls.
    Triggered if progress bar cleanup fails.
    """
    mock_build.return_value = [MagicMock()]
    # Force run_pool to fail to trigger exception block
    with patch(
        "pdfimgextract.extract.run_pool", side_effect=Exception("Trigger cleanup")
    ):
        mock_finish.side_effect = ValueError("Bar already closed")

        result = extract_images_parallel(mock_args)
        assert result == EXIT_FAILURE
        # If we reached here without a crash, suppress(Exception) worked.
