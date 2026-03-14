from unittest.mock import patch, MagicMock
from pdfimgextract.cli import main


@patch("pdfimgextract.cli.colorama_init")
@patch("pdfimgextract.cli.get_args")
@patch("pdfimgextract.cli.extract_images_parallel")
def test_main_execution_flow(mock_extract, mock_get_args, mock_colorama):
    """
    Verify that main() initializes colorama, retrieves arguments,
    and calls the extraction logic with correct parameters.
    """
    # 1. Setup Mock Arguments
    mock_args = MagicMock()
    mock_args.input = "input.pdf"
    mock_args.output = "output_folder"
    mock_args.parallelism = 4
    mock_args.overwrite = True
    mock_args.skip_dedup = False
    mock_get_args.return_value = mock_args

    # 2. Setup Mock Return Value for extraction
    mock_extract.return_value = 0

    # 3. Call main
    exit_code = main()

    # 4. Assertions
    # Ensure colorama was initialized
    mock_colorama.assert_called_once()

    # Ensure arguments were fetched
    mock_get_args.assert_called_once()

    # Ensure the extraction function was called with the mapped arguments
    mock_extract.assert_called_once_with(
        pdf_path="input.pdf",
        out_dir="output_folder",
        workers=4,
        overwrite=True,
        dedup=False,
    )

    # Ensure the exit code from extraction is returned by main
    assert exit_code == 0


@patch("pdfimgextract.cli.colorama_init")
@patch("pdfimgextract.cli.get_args")
@patch("pdfimgextract.cli.extract_images_parallel")
def test_main_returns_error_code(mock_extract, mock_get_args, mock_colorama):
    """Verify that main() propagates non-zero exit codes."""
    mock_get_args.return_value = MagicMock()
    mock_extract.return_value = 1

    exit_code = main()

    assert exit_code == 1
