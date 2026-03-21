import pytest
import sys
import os

from unittest.mock import patch

from pdfimgextract.args import get_args, Parser
from pdfimgextract.constants.exit_codes import EXIT_BY_INCORRECT_USAGE

# --- Fixtures ---


@pytest.fixture
def temp_pdf(tmp_path):
    """Create a real temporary PDF file to pass os.path.isfile validation."""
    pdf_file = tmp_path / "input.pdf"
    pdf_file.write_text("fake pdf data")
    return str(pdf_file)


# --- Success Path Tests ---


def test_get_args_full_positional(temp_pdf, tmp_path):
    """Test all three positional arguments."""
    output_dir = str(tmp_path / "output")
    with patch.object(sys, "argv", ["pdfimgextract", temp_pdf, output_dir, "4"]):
        args = get_args()
        assert args.pdf_path == temp_pdf
        assert args.out_dir == output_dir
        assert args.workers == 4
        assert args.dedup == "xref"


def test_get_args_optional_with_hash_dedup(temp_pdf, tmp_path):
    """Test optional flags and the 'hash' deduplication choice."""
    output_dir = str(tmp_path / "output")
    cmd = [
        "pdfimgextract",
        "-i",
        temp_pdf,
        "-o",
        output_dir,
        "-d",
        "hash",
        "--overwrite",
    ]
    with patch.object(sys, "argv", cmd):
        args = get_args()
        assert args.dedup == "hash"
        assert args.overwrite is True
        assert args.workers == 8  # fallback default


def test_normalization_precedence(temp_pdf, tmp_path):
    """Verify that optional flags override positional arguments."""
    output_dir = str(tmp_path / "output")
    # Provide 'wrong.pdf' positionally but 'temp_pdf' via flag
    cmd = ["pdfimgextract", "wrong.pdf", "wrong_dir", "-i", temp_pdf, "-o", output_dir]
    with patch.object(sys, "argv", cmd):
        args = get_args()
        assert args.pdf_path == temp_pdf
        assert args.out_dir == output_dir


# --- Error Handling & Branch Coverage ---


def test_parser_error_output_flow():
    """Ensure Parser.error calls print_help and exits correctly."""
    parser = Parser()
    with (
        patch.object(sys.stderr, "write") as mock_stderr,
        patch.object(Parser, "print_help") as mock_help,
    ):
        with pytest.raises(SystemExit) as excinfo:
            parser.error("invalid usage")

        assert excinfo.value.code == EXIT_BY_INCORRECT_USAGE
        mock_help.assert_called_once()
        # Check if the RED/ENDC constants or the word Error are in the write calls
        any_error_msg = any(
            "Error:" in str(call) for call in mock_stderr.call_args_list
        )
        assert any_error_msg


def test_invalid_dedup_choice(temp_pdf):
    """Trigger argparse's internal error via invalid choice."""
    cmd = ["pdfimgextract", temp_pdf, "out", "-d", "not-a-strategy"]
    with patch.object(sys, "argv", cmd):
        with pytest.raises(SystemExit) as excinfo:
            get_args()
        assert excinfo.value.code == EXIT_BY_INCORRECT_USAGE


def test_missing_input_logic(tmp_path):
    """Trigger 'if not args.input'."""
    with patch.object(sys, "argv", ["pdfimgextract"]):
        with pytest.raises(SystemExit):
            get_args()


def test_input_is_directory_error(tmp_path):
    """Trigger 'if not os.path.isfile' by providing a directory instead of a file."""
    dir_path = str(tmp_path / "is_a_dir")
    os.makedirs(dir_path)
    with patch.object(sys, "argv", ["pdfimgextract", "-i", dir_path, "-o", "out"]):
        with pytest.raises(SystemExit):
            get_args()


def test_missing_output_logic(temp_pdf):
    """Trigger 'if not args.output'."""
    with patch.object(sys, "argv", ["pdfimgextract", "-i", temp_pdf]):
        with pytest.raises(SystemExit):
            get_args()


def test_output_path_is_file_error(temp_pdf, tmp_path):
    """Trigger 'if os.path.exists(args.output) and not os.path.isdir'."""
    blocked_file = tmp_path / "file.txt"
    blocked_file.write_text("I am a file")
    with patch.object(sys, "argv", ["pdfimgextract", temp_pdf, str(blocked_file)]):
        with pytest.raises(SystemExit):
            get_args()


def test_parallelism_logic_branches(temp_pdf, tmp_path):
    """
    Cover 'args.parallelism < 1' and ensure
    'args.parallelism_pos or 8' logic is exercised.
    """
    out = str(tmp_path / "out")
    # Case: Negative parallelism
    with patch.object(sys, "argv", ["pdfimgextract", temp_pdf, out, "-5"]):
        with pytest.raises(SystemExit):
            get_args()


def test_version_flag():
    """Ensure --version exits with 0."""
    with patch.object(sys, "argv", ["pdfimgextract", "--version"]):
        with pytest.raises(SystemExit) as excinfo:
            get_args()
        assert excinfo.value.code == 0
