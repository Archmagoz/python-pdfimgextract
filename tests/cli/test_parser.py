import pytest
import sys

from unittest.mock import patch

from pdfimgextract.cli.parser import get_args, Parser
from pdfimgextract.models.datamodels import Args
from pdfimgextract.constants.exit_codes import EXIT_BY_INCORRECT_USAGE


class TestParser:
    """
    Validation suite for command-line argument parsing and normalization.
    Tests positional fallbacks, optional flags, and error handling.
    """

    @pytest.fixture
    def mock_pdf_file(self, tmp_path):
        """Creates a temporary dummy PDF file for validation tests."""
        pdf = tmp_path / "test.pdf"
        pdf.write_text("dummy content")
        return str(pdf)

    def test_parser_custom_error_handling(self):
        """
        Verify that the custom Parser class writes to stderr and
        exits with the specific EXIT_BY_INCORRECT_USAGE code.
        """
        parser = Parser()
        with patch.object(sys.stderr, "write") as mock_stderr:
            with pytest.raises(SystemExit) as excinfo:
                parser.error("Test Error Message")

            # Check custom exit code
            assert excinfo.value.code == EXIT_BY_INCORRECT_USAGE
            # Check if error message was formatted with RED/ENDC constants
            assert any(
                "Test Error Message" in call.args[0]
                for call in mock_stderr.call_args_list
            )

    def test_get_args_positional_success(self, mock_pdf_file, tmp_path):
        """Test parsing using positional arguments (input, output, workers)."""
        output_dir = str(tmp_path / "output")
        test_args = ["pdfimgextract", mock_pdf_file, output_dir, "4"]

        with patch.object(sys, "argv", test_args):
            args = get_args()

            assert isinstance(args, Args)
            assert args.pdf_path == mock_pdf_file
            assert args.out_dir == output_dir
            assert args.workers == 4
            assert args.overwrite is False  # Default

    def test_get_args_optional_flags_success(self, mock_pdf_file, tmp_path):
        """Test parsing using explicit optional flags (-i, -o, -p, --overwrite)."""
        output_dir = str(tmp_path / "output")
        test_args = [
            "pdfimgextract",
            "-i",
            mock_pdf_file,
            "-o",
            output_dir,
            "-p",
            "12",
            "--overwrite",
            "-d",
            "hash",
        ]

        with patch.object(sys, "argv", test_args):
            args = get_args()

            assert args.pdf_path == mock_pdf_file
            assert args.out_dir == output_dir
            assert args.workers == 12
            assert args.overwrite is True
            assert args.dedup == "hash"

    @pytest.mark.parametrize(
        "invalid_args, expected_error",
        [
            ([], "Missing input PDF file."),
            (["non_existent.pdf", "out"], "Input file not found or invalid"),
            (["test.pdf"], "Missing output directory."),
            (["test.pdf", "out", "0"], "Parallelism must be at least 1."),
        ],
    )
    def test_get_args_validation_errors(
        self, invalid_args, expected_error, mock_pdf_file
    ):
        """
        Test various validation failures to ensure 100% branch coverage
        of the 'if' statements in get_args.
        """
        # Adjust 'test.pdf' to be the real mock path if it's expected to exist
        cmd = ["pdfimgextract"] + [
            mock_pdf_file if a == "test.pdf" else a for a in invalid_args
        ]

        with patch.object(sys, "argv", cmd):
            with pytest.raises(SystemExit):
                get_args()

    def test_output_path_is_file_error(self, mock_pdf_file, tmp_path):
        """Test error when output directory path is actually an existing file."""
        existing_file = tmp_path / "not_a_dir.txt"
        existing_file.write_text("I am a file")

        test_args = ["pdfimgextract", mock_pdf_file, str(existing_file)]

        with patch.object(sys, "argv", test_args):
            with pytest.raises(SystemExit):
                get_args()
