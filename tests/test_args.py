import pytest
import sys

from unittest.mock import patch
from pdfimgextract.args import get_args, Parser
from pdfimgextract.exit_codes import EXIT_BY_INCORRECT_USAGE

# --- Fixtures ---


@pytest.fixture
def mock_argv():
    """Clear system arguments before each test to prevent leakage."""
    with patch.object(sys, "argv", ["pdfimgextract"]):
        yield


@pytest.fixture
def temp_pdf(tmp_path):
    """Create a real temporary PDF file to pass os.path.isfile validation."""
    pdf_file = tmp_path / "input.pdf"
    pdf_file.write_text("fake pdf data")
    return str(pdf_file)


# --- Success Path Tests ---


def test_get_args_positional_success(temp_pdf, tmp_path):
    """Test standard positional argument parsing."""
    output_dir = str(tmp_path / "output")
    with patch.object(sys, "argv", ["pdfimgextract", temp_pdf, output_dir, "4"]):
        args = get_args()
        assert args.input == temp_pdf
        assert args.output == output_dir
        assert args.parallelism == 4


def test_get_args_optional_success(temp_pdf, tmp_path):
    """Test optional flag parsing and overwrite boolean."""
    output_dir = str(tmp_path / "output")
    cmd = ["pdfimgextract", "-i", temp_pdf, "-o", output_dir, "-p", "2", "--overwrite"]
    with patch.object(sys, "argv", cmd):
        args = get_args()
        assert args.input == temp_pdf
        assert args.output == output_dir
        assert args.parallelism == 2
        assert args.overwrite is True


def test_get_args_default_parallelism(temp_pdf, tmp_path):
    """Ensure parallelism defaults to 8 if not provided."""
    output_dir = str(tmp_path / "output")
    with patch.object(sys, "argv", ["pdfimgextract", temp_pdf, output_dir]):
        args = get_args()
        assert args.parallelism == 8


# --- Error Handling & Logic Branch Coverage ---


def test_parser_custom_error_method():
    """Verify Parser.error writes to stderr and exits with custom code."""
    parser = Parser()
    with patch.object(sys.stderr, "write") as mock_stderr:
        with pytest.raises(SystemExit) as excinfo:
            parser.error("test error message")

        assert excinfo.value.code == EXIT_BY_INCORRECT_USAGE
        # Verify stderr contains the error message (ignoring color codes for simplicity)
        written_msg = mock_stderr.call_args[0][0]
        assert "Error: test error message" in written_msg


def test_missing_input_error():
    """Cover the 'if not args.input' branch."""
    with patch.object(sys, "argv", ["pdfimgextract"]):
        with pytest.raises(SystemExit):
            get_args()


def test_file_not_found_error(tmp_path):
    """Cover the 'if not os.path.isfile' branch."""
    missing_file = str(tmp_path / "ghost.pdf")
    with patch.object(sys, "argv", ["pdfimgextract", "-i", missing_file, "-o", "out"]):
        with pytest.raises(SystemExit):
            get_args()


def test_missing_output_error(temp_pdf):
    """Cover the 'if not args.output' branch."""
    with patch.object(sys, "argv", ["pdfimgextract", "-i", temp_pdf]):
        with pytest.raises(SystemExit):
            get_args()


def test_output_is_not_a_directory_error(temp_pdf, tmp_path):
    """Cover the branch where output path exists but is a file."""
    fake_dir_as_file = tmp_path / "blocker.txt"
    fake_dir_as_file.write_text("not a directory")

    cmd = ["pdfimgextract", "-i", temp_pdf, "-o", str(fake_dir_as_file)]
    with patch.object(sys, "argv", cmd):
        with pytest.raises(SystemExit):
            get_args()


def test_low_parallelism_error(temp_pdf, tmp_path):
    """Cover the 'args.parallelism < 1' branch."""
    with patch.object(sys, "argv", ["pdfimgextract", temp_pdf, "out", "0"]):
        with pytest.raises(SystemExit):
            get_args()


def test_version_output():
    """Trigger the argparse built-in version action."""
    with patch.object(sys, "argv", ["pdfimgextract", "--version"]):
        with pytest.raises(SystemExit) as excinfo:
            get_args()
        assert excinfo.value.code == 0
