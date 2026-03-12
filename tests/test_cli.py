from types import SimpleNamespace
from unittest.mock import Mock

from pdfimgextract.cli import main


def test_cli_main(monkeypatch):
    mock_args = SimpleNamespace(
        input="file.pdf",
        output="out",
        parallelism=4,
    )

    mock_colorama = Mock()
    mock_get_args = Mock(return_value=mock_args)
    mock_extract = Mock(return_value=0)

    monkeypatch.setattr(
        "pdfimgextract.cli.colorama_init",
        mock_colorama,
    )

    monkeypatch.setattr(
        "pdfimgextract.cli.get_args",
        mock_get_args,
    )

    monkeypatch.setattr(
        "pdfimgextract.cli.extract_images_parallel",
        mock_extract,
    )

    result = main()

    assert result == 0

    mock_colorama.assert_called_once()
    mock_get_args.assert_called_once()

    mock_extract.assert_called_once_with(
        pdf_path="file.pdf",
        out_dir="out",
        workers=4,
    )
