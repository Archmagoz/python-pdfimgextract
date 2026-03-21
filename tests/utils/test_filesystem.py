import os

from unittest.mock import patch

from pdfimgextract.utils.filesystem import (
    load_existing_stems,
    remove_file_safely,
    cleanup_stale_temp_files,
)


class TestFilesystemUtils:
    """
    Test suite for filesystem utilities.
    Uses tmp_path to ensure absolute isolation from the project directory.
    """

    @patch("os.path.isdir")
    def test_load_existing_stems_non_existent_dir(self, mock_isdir, tmp_path):
        """Verify empty set is returned if directory doesn't exist."""
        # Use a path within tmp_path that we haven't created
        fake_dir = str(tmp_path / "non_existent")
        mock_isdir.return_value = False

        assert load_existing_stems(fake_dir) == set()

    @patch("os.path.isdir")
    @patch("os.listdir")
    def test_load_existing_stems_success(self, mock_listdir, mock_isdir, tmp_path):
        """Verify file stems (filenames without extensions) are collected."""
        real_dir = str(tmp_path / "real_dir")
        mock_isdir.return_value = True
        mock_listdir.return_value = ["img001.png", "img002.jpg", "notes.txt"]

        expected = {"img001", "img002", "notes"}
        assert load_existing_stems(real_dir) == expected

    def test_remove_file_safely_none_path(self):
        """Ensure no action is taken if path is None."""
        # This should not trigger any filesystem activity or errors
        remove_file_safely(None)

    @patch("os.remove")
    def test_remove_file_safely_success(self, mock_remove, tmp_path):
        """Verify os.remove is called for a valid path within sandbox."""
        fake_file = str(tmp_path / "file.tmp")
        remove_file_safely(fake_file)
        mock_remove.assert_called_once_with(fake_file)

    @patch("os.remove")
    def test_remove_file_safely_suppresses_oserror(self, mock_remove, tmp_path):
        """Verify OSError is caught and suppressed (e.g., file not found)."""
        fake_file = str(tmp_path / "missing.tmp")
        mock_remove.side_effect = OSError("File not found")

        # Should not raise exception even if the OS call fails
        remove_file_safely(fake_file)

    @patch("os.path.isdir")
    def test_cleanup_stale_temp_files_no_dir(self, mock_isdir, tmp_path):
        """Ensure cleanup returns early if the directory is missing."""
        fake_dir = str(tmp_path / "missing_folder")
        mock_isdir.return_value = False

        with patch("os.listdir") as mock_listdir:
            cleanup_stale_temp_files(fake_dir)
            mock_listdir.assert_not_called()

    @patch("os.path.isdir")
    @patch("os.listdir")
    @patch("pdfimgextract.utils.filesystem.remove_file_safely")
    def test_cleanup_stale_temp_files_matching(
        self, mock_remove, mock_listdir, mock_isdir, tmp_path
    ):
        """Verify only files matching the specific pattern are removed."""
        # Setup a sandboxed directory path
        sandbox_dir = tmp_path / "cleanup_test"
        sandbox_dir.mkdir()
        sandbox_dir_str = str(sandbox_dir)

        mock_isdir.return_value = True
        mock_listdir.return_value = [
            ".pdfimgextract-tmp-abc-001.png.part",  # Match
            "final_image.png",  # No match (prefix)
            ".pdfimgextract-tmp-xyz-002.jpg",  # No match (suffix)
            ".pdfimgextract-tmp-123.part",  # Match
        ]

        cleanup_stale_temp_files(sandbox_dir_str)

        # Verify only matching files were passed to removal with the correct full path
        assert mock_remove.call_count == 2

        expected_match_1 = os.path.join(
            sandbox_dir_str, ".pdfimgextract-tmp-abc-001.png.part"
        )
        expected_match_2 = os.path.join(sandbox_dir_str, ".pdfimgextract-tmp-123.part")

        mock_remove.assert_any_call(expected_match_1)
        mock_remove.assert_any_call(expected_match_2)
