import pytest
import os

from dataclasses import replace
from unittest.mock import patch

from pdfimgextract.core.commit import finalize_result
from pdfimgextract.models.datamodels import ExtractResult


class TestCommit:
    """
    Test suite for the result finalization logic.
    Handles immutable (frozen) dataclasses using dataclasses.replace.
    """

    @pytest.fixture
    def successful_result(self):
        """
        Returns a valid ExtractResult object mimicking a successful worker task.
        """
        return ExtractResult(
            ok=True,
            cancelled=False,
            xref=10,
            stem="001",
            ext="png",
            temp_path="/tmp/001.tmp",
            error=None,
        )

    def test_finalize_result_success(self, successful_result):
        """
        Test the happy path: valid result and successful os.replace.
        """
        out_dir = "/final/path"
        expected_final_path = os.path.join(out_dir, "001.png")

        with patch("os.replace") as mock_replace:
            final_res, path = finalize_result(successful_result, out_dir)

            mock_replace.assert_called_once_with(
                successful_result.temp_path, expected_final_path
            )
            assert final_res.ok is True
            assert final_res.temp_path is None
            assert path == expected_final_path

    def test_finalize_result_already_failed(self):
        """
        Ensure that if the result is already marked as not 'ok',
        it returns immediately without attempting any IO.
        """
        failed_res = ExtractResult(
            ok=False,
            cancelled=False,
            xref=1,
            stem="1",
            ext="jpg",
            temp_path=None,
            error="Earlier failure",
        )

        with patch("os.replace") as mock_replace:
            res, path = finalize_result(failed_res, "dir")

            assert res == failed_res
            assert path is None
            mock_replace.assert_not_called()

    def test_finalize_result_missing_temp_path(self, successful_result):
        """
        Covers the branch where 'ok' is True but 'temp_path' is missing.
        Uses dataclasses.replace to handle the frozen instance.
        """
        # Create a new instance with temp_path as None
        modified_result = replace(successful_result, temp_path=None)

        res, path = finalize_result(modified_result, "dir")

        assert res.ok is False
        assert path is None
        assert res.error == "Invalid worker result: missing temp_path"

    def test_finalize_result_missing_extension(self, successful_result):
        """
        Covers the branch where extension is missing.
        Uses dataclasses.replace to handle the frozen instance.
        """
        # Create a new instance with ext as None
        modified_result = replace(successful_result, ext=None)

        with patch("pdfimgextract.core.commit.remove_file_safely") as mock_remove:
            res, path = finalize_result(modified_result, "dir")

            mock_remove.assert_called_once_with(modified_result.temp_path)
            assert res.ok is False
            assert res.error == "Invalid worker result: missing extension"
            assert path is None

    def test_finalize_result_os_error_during_replace(self, successful_result):
        """
        Test handling of OSError during the atomic rename process.
        """
        error_msg = "Permission Denied"
        with patch("os.replace", side_effect=OSError(error_msg)):
            with patch("pdfimgextract.core.commit.remove_file_safely") as mock_remove:
                res, path = finalize_result(successful_result, "dir")

                assert res.ok is False
                assert str(res.error) == error_msg
                mock_remove.assert_called_once_with(successful_result.temp_path)
                assert path is None

    @pytest.mark.parametrize("error_msg", ["Disk Full", "Cross-device link"])
    def test_finalize_result_various_os_errors(self, successful_result, error_msg):
        """
        Parametrized test to ensure different OS error messages
        are correctly captured.
        """
        with patch("os.replace", side_effect=OSError(error_msg)):
            with patch("pdfimgextract.core.commit.remove_file_safely"):
                res, _ = finalize_result(successful_result, "dir")
                assert res.error == error_msg
