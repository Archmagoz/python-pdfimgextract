import os

from unittest.mock import patch

from pdfimgextract.commit import finalize_result
from pdfimgextract.datamodels import ExtractResult

# --- Helper ---


def create_base_result(
    ok: bool = True,
    temp_path: str | None = "tmp/file.part",
    ext: str | None = "png",
    stem: str = "01",
) -> ExtractResult:
    return ExtractResult(
        ok=ok,
        cancelled=False,
        xref=100,
        stem=stem,
        ext=ext,
        temp_path=temp_path,
        error=None,
    )


# --- Tests ---


def test_finalize_result_already_failed():
    """Branch: if not result.ok"""
    initial_result = create_base_result(ok=False)
    result, path = finalize_result(initial_result, "out")

    assert result == initial_result
    assert path is None


def test_finalize_result_missing_temp_path():
    """Branch: if result.temp_path is None"""
    # Using # type: ignore if your linter complains about passing None to a str param
    initial_result = create_base_result(temp_path=None)  # type: ignore
    result, path = finalize_result(initial_result, "out")

    assert result.ok is False
    assert result.error is not None
    assert "missing temp_path" in result.error
    assert path is None


def test_finalize_result_missing_extension():
    """Branch: if not result.ext"""
    initial_result = create_base_result(ext=None)

    with patch("pdfimgextract.commit.remove_file_safely") as mock_remove:
        result, path = finalize_result(initial_result, "out")

        mock_remove.assert_called_once_with(initial_result.temp_path)
        assert result.ok is False
        assert result.error is not None
        assert "missing extension" in result.error


@patch("os.replace")
def test_finalize_result_os_error_during_replace(mock_replace):
    """Branch: except OSError as e"""
    mock_replace.side_effect = OSError("Disk full")
    initial_result = create_base_result()

    with patch("pdfimgextract.commit.remove_file_safely") as mock_remove:
        result, path = finalize_result(initial_result, "out")

        mock_remove.assert_called_once_with(initial_result.temp_path)
        assert result.ok is False
        assert result.error is not None
        assert "Disk full" in result.error
        assert path is None


@patch("os.replace")
def test_finalize_result_success(mock_replace):
    """Branch: Final successful return"""
    initial_result = create_base_result(stem="image_01", ext="jpg")
    out_dir = "output_folder"

    result, path = finalize_result(initial_result, out_dir)

    expected_path = os.path.join(out_dir, "image_01.jpg")
    mock_replace.assert_called_once_with(initial_result.temp_path, expected_path)

    assert result.ok is True
    assert path == expected_path
    assert result.temp_path is None  # It's cleared on success
