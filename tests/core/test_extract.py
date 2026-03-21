import pytest

from unittest.mock import patch, MagicMock, mock_open

from pdfimgextract.core.extract import extract_images_parallel
from pdfimgextract.models.datamodels import Args
from pdfimgextract.constants.exit_codes import EXIT_SUCCESS, EXIT_FAILURE, EXIT_BY_USER


class TestExtract:
    """
    Test suite for the extraction orchestration logic.
    Ensures zero filesystem impact by mocking directory creation.
    """

    @pytest.fixture
    def mock_args(self):
        """Standard mock arguments for extraction tasks."""
        return Args(
            pdf_path="input.pdf",
            out_dir="output_dir",
            workers=4,
            overwrite=False,
            dedup="xref",
        )

    @patch("pdfimgextract.core.extract.print_summary")
    @patch("pdfimgextract.core.extract.cleanup_stale_temp_files")
    @patch("pdfimgextract.core.extract.os.makedirs")
    @patch("pdfimgextract.core.extract.create_progress_bar")
    @patch("pdfimgextract.core.extract.run_pool")
    @patch("pdfimgextract.core.extract.build_tasks")
    def test_extract_success_flow(
        self,
        mock_tasks,
        mock_run,
        mock_pb,
        mock_mkdir,
        mock_cleanup,
        mock_summary,
        mock_args,
    ):
        """Tests the standard successful execution path."""
        mock_tasks.return_value = [MagicMock()]
        mock_run.return_value = ([], [], 1, False)

        summary_obj = MagicMock(interrupted=False, failed=0)
        mock_summary.return_value = summary_obj

        exit_code = extract_images_parallel(mock_args)

        assert exit_code == EXIT_SUCCESS
        mock_mkdir.assert_called_once_with(mock_args.out_dir, exist_ok=True)

    @patch("pdfimgextract.core.extract.os.makedirs")
    @patch("pdfimgextract.core.extract.build_tasks")
    def test_extract_no_tasks(self, mock_tasks, mock_mkdir, mock_args):
        """Ensures early exit and no directory creation if no images are found."""
        mock_tasks.return_value = []

        exit_code = extract_images_parallel(mock_args)

        assert exit_code == EXIT_SUCCESS
        mock_mkdir.assert_not_called()

    @patch("pdfimgextract.core.extract.os.makedirs")
    @patch("pdfimgextract.core.extract.cleanup_stale_temp_files")
    @patch("pdfimgextract.core.extract.run_pool")
    @patch("pdfimgextract.core.extract.create_progress_bar")
    @patch("pdfimgextract.core.extract.build_tasks")
    def test_extract_keyboard_interrupt(
        self, mock_tasks, mock_pb, mock_run, mock_cleanup, mock_mkdir, mock_args
    ):
        """Tests graceful user interruption (KeyboardInterrupt) handling."""
        mock_tasks.return_value = [MagicMock()]
        mock_run.side_effect = KeyboardInterrupt()

        with patch("sys.stderr", new_callable=mock_open()):
            exit_code = extract_images_parallel(mock_args)
            assert exit_code == EXIT_BY_USER
            # Verify directory creation was attempted but intercepted
            mock_mkdir.assert_called_once()

    @patch("pdfimgextract.core.extract.os.makedirs")
    @patch("pdfimgextract.core.extract.cleanup_stale_temp_files")
    @patch("pdfimgextract.core.extract.run_pool")
    @patch("pdfimgextract.core.extract.create_progress_bar")
    @patch("pdfimgextract.core.extract.build_tasks")
    def test_extract_fatal_error(
        self, mock_tasks, mock_pb, mock_run, mock_cleanup, mock_mkdir, mock_args
    ):
        """Tests handling of unexpected fatal runtime errors."""
        mock_tasks.return_value = [MagicMock()]
        mock_run.side_effect = RuntimeError("Process crashed")

        with patch("sys.stderr", new_callable=mock_open()):
            exit_code = extract_images_parallel(mock_args)
            assert exit_code == EXIT_FAILURE
            mock_mkdir.assert_called_once()

    @patch("pdfimgextract.core.extract.os.makedirs")
    @patch("pdfimgextract.core.extract.print_summary")
    @patch("pdfimgextract.core.extract.run_pool")
    @patch("pdfimgextract.core.extract.build_tasks")
    def test_extract_failure_due_to_failed_items(
        self, mock_tasks, mock_run, mock_summary, mock_mkdir, mock_args
    ):
        """Tests that failures during worker processing return EXIT_FAILURE."""
        mock_tasks.return_value = [MagicMock()]
        mock_run.return_value = ([], [MagicMock()], 0, False)

        summary_obj = MagicMock(interrupted=False, failed=1)
        mock_summary.return_value = summary_obj

        exit_code = extract_images_parallel(mock_args)
        assert exit_code == EXIT_FAILURE
        mock_mkdir.assert_called_once()

    @patch("pdfimgextract.core.extract.os.makedirs")
    @patch("pdfimgextract.core.extract.finish_progress_bar")
    @patch("pdfimgextract.core.extract.run_pool")
    @patch("pdfimgextract.core.extract.create_progress_bar")
    @patch("pdfimgextract.core.extract.build_tasks")
    def test_progress_bar_cleanup_exception_suppression(
        self, mock_tasks, mock_pb, mock_run, mock_finish, mock_mkdir, mock_args
    ):
        """Verifies that progress bar errors do not crash the main process."""
        mock_tasks.return_value = [MagicMock()]
        # Simulate tqdm error during finalization
        mock_finish.side_effect = Exception("TQDM Error")

        exit_code = extract_images_parallel(mock_args)

        assert exit_code == EXIT_FAILURE
        mock_mkdir.assert_called_once()
