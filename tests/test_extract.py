import pytest

from unittest.mock import MagicMock, patch
from pdfimgextract.extract import extract_images_parallel
from pdfimgextract.exit_codes import EXIT_SUCCESS, EXIT_FAILURE
from pdfimgextract.datamodels import Args

# --- Fixtures ---


@pytest.fixture
def mock_args(tmp_path):
    """
    Use tmp_path to ensure any file operations happen in
    a sandbox that is automatically deleted after tests.
    """
    return Args(
        pdf_path=str(tmp_path / "input.pdf"),
        out_dir=str(tmp_path / "output_dir"),
        workers=4,
        overwrite=False,
        dedup="xref",
    )


# --- Success Path Tests ---


@patch("pdfimgextract.extract.build_tasks")
def test_extract_no_tasks(mock_build, mock_args, capsys):
    """Cover the 'if total == 0' branch (no images found)."""
    mock_build.return_value = []

    result = extract_images_parallel(mock_args)

    assert result == EXIT_SUCCESS
    captured = capsys.readouterr()
    assert "No images found" in captured.out


@patch("pdfimgextract.extract.build_tasks")
@patch("pdfimgextract.extract.create_progress_bar")
@patch("pdfimgextract.extract.run_pool")
@patch("pdfimgextract.extract.print_summary")
@patch("pdfimgextract.extract.os.makedirs")  # Intercept directory creation
@patch("pdfimgextract.extract.cleanup_stale_temp_files")
@patch("pdfimgextract.extract.finish_progress_bar")
def test_extract_full_success_flow(
    mock_finish,
    mock_cleanup,
    mock_mkdir,
    mock_summary,
    mock_pool,
    mock_pb,
    mock_build,
    mock_args,
):
    """Cover the 'else' block and full successful completion."""
    # Setup: 1 task, pool succeeds
    mock_build.return_value = [MagicMock()]
    mock_pool.return_value = ([], [], 1, False)

    # Mock summary object return values
    mock_sum_obj = MagicMock()
    mock_sum_obj.interrupted = False
    mock_sum_obj.failed = 0
    mock_summary.return_value = mock_sum_obj

    result = extract_images_parallel(mock_args)

    assert result == EXIT_SUCCESS
    mock_mkdir.assert_called_with(mock_args.out_dir, exist_ok=True)
    mock_cleanup.assert_called_once()
    mock_finish.assert_called_once()


# --- Exception & Error Branch Tests ---


@patch("pdfimgextract.extract.build_tasks")
@patch("pdfimgextract.extract.create_progress_bar")
@patch("pdfimgextract.extract.run_pool")
@patch("pdfimgextract.extract.cleanup_stale_temp_files")
def test_extract_keyboard_interrupt_branch(
    mock_cleanup, mock_pool, mock_pb, mock_build, mock_args, capsys
):
    """Cover the 'except KeyboardInterrupt' block."""
    mock_build.return_value = [MagicMock()]
    # Trigger interrupt during pool execution
    mock_pool.side_effect = KeyboardInterrupt()

    result = extract_images_parallel(mock_args)

    assert result == EXIT_FAILURE
    mock_cleanup.assert_called_once()
    captured = capsys.readouterr()
    assert "interrupted by user" in captured.err


@patch("pdfimgextract.extract.build_tasks")
@patch("pdfimgextract.extract.cleanup_stale_temp_files")
def test_extract_fatal_exception_branch(mock_cleanup, mock_build, mock_args, capsys):
    """Cover the generic 'except Exception' block."""
    # Force a random fatal error
    mock_build.side_effect = RuntimeError("Disk Failure")

    result = extract_images_parallel(mock_args)

    assert result == EXIT_FAILURE
    mock_cleanup.assert_called_once()
    captured = capsys.readouterr()
    assert "Fatal error: Disk Failure" in captured.err


@patch("pdfimgextract.extract.build_tasks")
@patch("pdfimgextract.extract.run_pool")
@patch("pdfimgextract.extract.print_summary")
def test_extract_failure_summary_branch(mock_summary, mock_pool, mock_build, mock_args):
    """Cover the branch where summary reports failed tasks."""
    mock_build.return_value = [MagicMock()]
    mock_pool.return_value = ([], ["error_log"], 0, False)

    # Summary says tasks failed
    mock_sum_obj = MagicMock()
    mock_sum_obj.interrupted = False
    mock_sum_obj.failed = 5
    mock_summary.return_value = mock_sum_obj

    result = extract_images_parallel(mock_args)

    assert result == EXIT_FAILURE


@patch("pdfimgextract.extract.build_tasks")
@patch("pdfimgextract.extract.create_progress_bar")
@patch("pdfimgextract.extract.finish_progress_bar")
def test_extract_suppress_exception_in_cleanup(
    mock_finish, mock_pb, mock_build, mock_args
):
    """Cover the 'with suppress(Exception)' logic inside finish_progress_bar calls."""
    mock_build.return_value = [MagicMock()]
    # Force a crash to trigger the cleanup block
    with patch("pdfimgextract.extract.run_pool", side_effect=Exception("Crash")):
        # Make the progress bar cleanup itself crash
        mock_finish.side_effect = ValueError("Already closed")

        result = extract_images_parallel(mock_args)
        # Should still return EXIT_FAILURE from the main crash,
        # but the ValueError should have been suppressed.
        assert result == EXIT_FAILURE
