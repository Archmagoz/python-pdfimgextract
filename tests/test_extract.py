from unittest.mock import patch, MagicMock

from pdfimgextract.extract import extract_images_parallel
from pdfimgextract.exit_codes import EXIT_SUCCESS, EXIT_FAILURE

# --- Success and Early Exit Tests ---


def test_extract_images_parallel_no_tasks():
    """Covers: if total == 0"""
    with patch("os.makedirs"):
        with patch("pdfimgextract.extract.build_tasks", return_value=[]):
            result = extract_images_parallel("in.pdf", "out", 4, False)
            assert result == EXIT_SUCCESS


@patch("pdfimgextract.extract.print_summary")
@patch("pdfimgextract.extract.run_pool")
@patch("pdfimgextract.extract.create_progress_bar")
@patch("pdfimgextract.extract.build_tasks")
@patch("os.makedirs")
def test_extract_images_parallel_success(
    mock_mkdir, mock_build, mock_pb, mock_pool, mock_summary
):
    """Covers: Normal completion and the 'else' block."""
    mock_build.return_value = [MagicMock()]
    mock_pool.return_value = ([], [], 1, False)

    mock_summary_obj = MagicMock()
    mock_summary_obj.interrupted = False
    mock_summary_obj.failed = 0
    mock_summary.return_value = mock_summary_obj

    with patch("pdfimgextract.extract.cleanup_stale_temp_files"):
        with patch("pdfimgextract.extract.finish_progress_bar"):
            result = extract_images_parallel("in.pdf", "out", 4, False)
            assert result == EXIT_SUCCESS


# --- The "Missing 8%" Coverage Tests ---


@patch("pdfimgextract.extract.build_tasks")
@patch("pdfimgextract.extract.create_progress_bar")
def test_keyboard_interrupt_with_active_progress(mock_pb, mock_build):
    """
    Covers: 'except KeyboardInterrupt' AND 'if progress is not None'.
    This forces the cleanup and progress bar finalization.
    """
    mock_build.return_value = [MagicMock()]
    mock_pb.return_value = MagicMock()
    # Force interrupt during run_pool execution
    with patch("pdfimgextract.extract.run_pool", side_effect=KeyboardInterrupt):
        with patch("pdfimgextract.extract.cleanup_stale_temp_files"):
            with patch("pdfimgextract.extract.finish_progress_bar") as mock_finish:
                result = extract_images_parallel("in.pdf", "out", 4, False)
                assert result == EXIT_FAILURE
                mock_finish.assert_called_once()


@patch("pdfimgextract.extract.build_tasks")
def test_fatal_error_without_progress(mock_build):
    """
    Covers: 'except Exception as e' AND 'if progress is None'.
    This hits the case where the crash happens BEFORE the progress bar exists.
    """
    mock_build.side_effect = RuntimeError("Early crash")
    with patch("pdfimgextract.extract.cleanup_stale_temp_files"):
        # sys.stderr.write check can be added if needed
        result = extract_images_parallel("in.pdf", "out", 4, False)
        assert result == EXIT_FAILURE


def test_summary_indicates_failure():
    """Covers: The final 'if summary.interrupted or summary.failed > 0' branch."""
    with patch("os.makedirs"):
        with patch("pdfimgextract.extract.build_tasks", return_value=[MagicMock()]):
            with patch("pdfimgextract.extract.create_progress_bar"):
                with patch(
                    "pdfimgextract.extract.run_pool", return_value=([], [], 0, False)
                ):
                    with patch("pdfimgextract.extract.cleanup_stale_temp_files"):
                        with patch("pdfimgextract.extract.finish_progress_bar"):
                            mock_summary = MagicMock(failed=1, interrupted=False)
                            with patch(
                                "pdfimgextract.extract.print_summary",
                                return_value=mock_summary,
                            ):
                                result = extract_images_parallel(
                                    "in.pdf", "out", 4, False
                                )
                                assert result == EXIT_FAILURE


@patch("pdfimgextract.extract.finish_progress_bar")
def test_suppress_exception_in_cleanup(mock_finish):
    """Covers: the 'with suppress(Exception)' block inside handlers."""
    mock_finish.side_effect = AttributeError("Tqdm error")
    with patch("os.makedirs"):
        # Trigger an error after progress bar is created to hit the suppress block
        with patch("pdfimgextract.extract.build_tasks", return_value=[MagicMock()]):
            with patch("pdfimgextract.extract.create_progress_bar"):
                with patch("pdfimgextract.extract.run_pool", side_effect=Exception):
                    with patch("pdfimgextract.extract.cleanup_stale_temp_files"):
                        result = extract_images_parallel("in.pdf", "out", 4, False)
                        assert result == EXIT_FAILURE
