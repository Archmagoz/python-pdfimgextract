import pytest

from unittest.mock import patch, MagicMock, mock_open

from pdfimgextract.core.extract import extract_images_parallel
from pdfimgextract.models.datamodels import Args
from pdfimgextract.constants.exit_codes import EXIT_SUCCESS, EXIT_FAILURE, EXIT_BY_USER


class TestExtract:
    """
    Orchestration suite for the parallel extraction process.
    Tests process lifecycle, error handling, and cleanup procedures.
    """

    @pytest.fixture
    def mock_args(self):
        """Standard arguments fixture for testing."""
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
        """
        Test a full successful extraction flow.
        Verifies directory creation and correct exit code.
        """
        # Arrange: Tasks exist
        mock_tasks.return_value = [MagicMock()]
        # Mock run_pool: (results, failed, success_count, interrupted)
        mock_run.return_value = ([], [], 1, False)

        # Mock summary object with specific attributes to pass the success gate
        summary_obj = MagicMock()
        summary_obj.interrupted = False
        summary_obj.failed = 0
        mock_summary.return_value = summary_obj

        # Act
        exit_code = extract_images_parallel(mock_args)

        # Assert
        assert exit_code == EXIT_SUCCESS
        mock_mkdir.assert_called_once_with(mock_args.out_dir, exist_ok=True)
        mock_cleanup.assert_called_once_with(mock_args.out_dir)

    @patch("pdfimgextract.core.extract.os.makedirs")
    @patch("pdfimgextract.core.extract.build_tasks")
    def test_extract_no_tasks(self, mock_tasks, mock_mkdir, mock_args):
        """
        Ensure early return and no directory creation when no images are found.
        """
        mock_tasks.return_value = []

        exit_code = extract_images_parallel(mock_args)

        assert exit_code == EXIT_SUCCESS
        mock_mkdir.assert_not_called()

    @patch("pdfimgextract.core.extract.cleanup_stale_temp_files")
    @patch("pdfimgextract.core.extract.run_pool")
    @patch("pdfimgextract.core.extract.create_progress_bar")
    @patch("pdfimgextract.core.extract.build_tasks")
    def test_extract_keyboard_interrupt(
        self, mock_tasks, mock_pb, mock_run, mock_cleanup, mock_args
    ):
        """
        Verify graceful handling and cleanup during a KeyboardInterrupt.
        """
        mock_tasks.return_value = [MagicMock()]
        mock_run.side_effect = KeyboardInterrupt()

        with patch("sys.stderr", new_callable=mock_open()):
            exit_code = extract_images_parallel(mock_args)

            assert exit_code == EXIT_BY_USER
            mock_cleanup.assert_called_once_with(mock_args.out_dir)

    @patch("pdfimgextract.core.extract.cleanup_stale_temp_files")
    @patch("pdfimgextract.core.extract.run_pool")
    @patch("pdfimgextract.core.extract.create_progress_bar")
    @patch("pdfimgextract.core.extract.build_tasks")
    def test_extract_fatal_error(
        self, mock_tasks, mock_pb, mock_run, mock_cleanup, mock_args
    ):
        """
        Verify generic exceptions return EXIT_FAILURE and trigger cleanup.
        """
        mock_tasks.return_value = [MagicMock()]
        mock_run.side_effect = RuntimeError("Process crashed")

        with patch("sys.stderr", new_callable=mock_open()):
            exit_code = extract_images_parallel(mock_args)

            assert exit_code == EXIT_FAILURE
            mock_cleanup.assert_called_once_with(mock_args.out_dir)

    @patch("pdfimgextract.core.extract.print_summary")
    @patch("pdfimgextract.core.extract.run_pool")
    @patch("pdfimgextract.core.extract.build_tasks")
    def test_extract_failure_due_to_failed_items(
        self, mock_tasks, mock_run, mock_summary, mock_args
    ):
        """
        Test that EXIT_FAILURE is returned if the summary shows failed extractions.
        """
        mock_tasks.return_value = [MagicMock()]
        mock_run.return_value = ([], [MagicMock()], 0, False)

        summary_obj = MagicMock()
        summary_obj.interrupted = False
        summary_obj.failed = 1
        mock_summary.return_value = summary_obj

        exit_code = extract_images_parallel(mock_args)

        assert exit_code == EXIT_FAILURE

    @patch("pdfimgextract.core.extract.finish_progress_bar")
    @patch("pdfimgextract.core.extract.run_pool")
    @patch("pdfimgextract.core.extract.create_progress_bar")
    @patch("pdfimgextract.core.extract.build_tasks")
    def test_progress_bar_cleanup_exception_suppression(
        self, mock_tasks, mock_pb, mock_run, mock_finish, mock_args
    ):
        """
        Verify that errors in progress bar finalization are suppressed.
        """
        mock_tasks.return_value = [MagicMock()]
        mock_finish.side_effect = Exception("TQDM Error")

        # Should not raise exception
        exit_code = extract_images_parallel(mock_args)
        assert exit_code is not None
