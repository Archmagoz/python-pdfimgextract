import pytest
from unittest.mock import patch, MagicMock
from pdfimgextract.cli import main
from pdfimgextract.exit_codes import EXIT_SUCCESS, EXIT_FAILURE

# --- CLI Tests ---


@patch("pdfimgextract.cli.colorama_init")
@patch("pdfimgextract.cli.get_args")
@patch("pdfimgextract.cli.extract_images_parallel")
def test_main_success_flow(mock_extract, mock_get_args, mock_colorama):
    """Verify that main initializes colorama, gets args, and returns success."""
    # Setup mocks
    mock_args_obj = MagicMock()
    mock_get_args.return_value = mock_args_obj
    mock_extract.return_value = EXIT_SUCCESS

    # Execute
    result = main()

    # Assertions
    mock_colorama.assert_called_once()
    mock_get_args.assert_called_once()
    mock_extract.assert_called_once_with(mock_args_obj)
    assert result == EXIT_SUCCESS


@patch("pdfimgextract.cli.get_args")
@patch("pdfimgextract.cli.extract_images_parallel")
def test_main_failure_flow(mock_extract, mock_get_args):
    """Verify that main propagates failure exit codes from the extractor."""
    mock_get_args.return_value = MagicMock()
    mock_extract.return_value = EXIT_FAILURE

    result = main()

    assert result == EXIT_FAILURE


@patch("pdfimgextract.cli.get_args")
def test_main_arg_parse_error(mock_get_args):
    """
    Verify behavior if get_args raises SystemExit (standard argparse behavior).
    Note: get_args internally calls sys.exit on error, so we catch it here.
    """
    mock_get_args.side_effect = SystemExit(2)

    with pytest.raises(SystemExit) as excinfo:
        main()

    assert excinfo.value.code == 2
