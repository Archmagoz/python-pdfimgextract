from unittest.mock import patch

from pdfimgextract.api import extract_images_parallel
from pdfimgextract.models.datamodels import Args


class TestApi:
    """
    Test suite for the public API layer.
    Ensures parameters are correctly transformed into internal Args models.
    """

    @patch("pdfimgextract.api._extract")
    def test_extract_images_parallel_mapping(self, mock_core_extract):
        """
        Verify that arguments passed to the API are correctly
        packaged into an Args object and passed to the core logic.
        """
        # Arrange
        pdf = "input.pdf"
        out = "output_folder"
        workers = 12
        overwrite = True
        dedup = "hash"

        mock_core_extract.return_value = 0  # EXIT_SUCCESS

        # Act
        result = extract_images_parallel(
            pdf, out, workers=workers, overwrite=overwrite, dedup=dedup
        )

        # Assert
        assert result == 0

        # Verify that the internal _extract was called with the correct Args instance
        args_passed = mock_core_extract.call_args[0][0]
        assert isinstance(args_passed, Args)
        assert args_passed.pdf_path == pdf
        assert args_passed.out_dir == out
        assert args_passed.workers == workers
        assert args_passed.overwrite is True
        assert args_passed.dedup == "hash"

    @patch("pdfimgextract.api._extract")
    def test_extract_images_parallel_defaults(self, mock_core_extract):
        """
        Verify that the API uses the correct default values
        when optional arguments are omitted.
        """
        mock_core_extract.return_value = 0

        extract_images_parallel("test.pdf", "out")

        args_passed = mock_core_extract.call_args[0][0]
        # Check against your function signatures' default values
        assert args_passed.workers == 8
        assert args_passed.overwrite is False
        assert args_passed.dedup == "xref"
