import pytest

from unittest.mock import patch, MagicMock

from pdfimgextract.cli.cli import main
from pdfimgextract.models.datamodels import Args


class TestCLI:
    """
    Suite of tests for the CLI entry point.
    Focuses on orchestration between parser and core execution.
    """

    @patch("pdfimgextract.cli.cli.colorama_init")
    @patch("pdfimgextract.cli.cli.get_args")
    @patch("pdfimgextract.cli.cli.extract_images_parallel")
    def test_main_execution_flow(self, mock_extract, mock_get_args, mock_colorama):
        """
        Test if main initializes colorama, parses arguments,
        and calls the parallel extraction with the correct object.
        """
        # Arrange: Setup mock return values
        mock_args = MagicMock(spec=Args)
        mock_get_args.return_value = mock_args
        mock_extract.return_value = 0

        # Act: Execute the entry point
        exit_code = main()

        # Assert: Verify the orchestration logic
        mock_colorama.assert_called_once()
        mock_get_args.assert_called_once()
        mock_extract.assert_called_once_with(mock_args)
        assert exit_code == 0

    @patch("pdfimgextract.cli.cli.colorama_init")
    @patch("pdfimgextract.cli.cli.get_args")
    @patch("pdfimgextract.cli.cli.extract_images_parallel")
    @pytest.mark.parametrize("expected_exit_code", [0, 1, 127])
    def test_main_returns_correct_exit_codes(
        self, mock_extract, mock_get_args, mock_colorama, expected_exit_code
    ):
        """
        Ensure that main propagates the exit code returned by the core logic.
        """
        # Arrange
        mock_get_args.return_value = MagicMock(spec=Args)
        mock_extract.return_value = expected_exit_code

        # Act
        result = main()

        # Assert
        assert result == expected_exit_code
