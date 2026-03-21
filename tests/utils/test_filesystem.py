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
    Ensures safe file handling and accurate state scanning.
    """

    @patch("os.path.isdir")
    def test_load_existing_stems_non_existent_dir(self, mock_isdir):
        """Verify empty set is returned if directory doesn't exist."""
        mock_isdir.return_value = False
        assert load_existing_stems("fake_dir") == set()

    @patch("os.path.isdir")
    @patch("os.listdir")
    def test_load_existing_stems_success(self, mock_listdir, mock_isdir):
        """Verify file stems (filenames without extensions) are collected."""
        mock_isdir.return_value = True
        mock_listdir.return_value = ["img001.png", "img002.jpg", "notes.txt"]

        expected = {"img001", "img002", "notes"}
        assert load_existing_stems("real_dir") == expected

    def test_remove_file_safely_none_path(self):
        """Ensure no action is taken if path is None."""
        # This shouldn't raise any error
        remove_file_safely(None)

    @patch("os.remove")
    def test_remove_file_safely_success(self, mock_remove):
        """Verify os.remove is called for a valid path."""
        remove_file_safely("path/to/file.tmp")
        mock_remove.assert_called_once_with("path/to/file.tmp")

    @patch("os.remove")
    def test_remove_file_safely_suppresses_oserror(self, mock_remove):
        """Verify OSError is caught and suppressed (e.g., file not found)."""
        mock_remove.side_effect = OSError("File not found")
        # Should not raise exception
        remove_file_safely("missing_file.tmp")

    @patch("os.path.isdir")
    def test_cleanup_stale_temp_files_no_dir(self, mock_isdir):
        """Ensure cleanup returns early if the directory is missing."""
        mock_isdir.return_value = False
        # Should not call listdir
        with patch("os.listdir") as mock_listdir:
            cleanup_stale_temp_files("fake_dir")
            mock_listdir.assert_not_called()

    @patch("os.path.isdir")
    @patch("os.listdir")
    @patch("pdfimgextract.utils.filesystem.remove_file_safely")
    def test_cleanup_stale_temp_files_matching(
        self, mock_remove, mock_listdir, mock_isdir
    ):
        """Verify only files matching the specific pattern are removed."""
        mock_isdir.return_value = True
        mock_listdir.return_value = [
            ".pdfimgextract-tmp-abc-001.png.part",  # Match
            "final_image.png",  # No match (prefix)
            ".pdfimgextract-tmp-xyz-002.jpg",  # No match (suffix)
            ".pdfimgextract-tmp-123.part",  # Match
        ]

        cleanup_stale_temp_files("out")

        # Verify only the two matching files were passed to the removal function
        assert mock_remove.call_count == 2
        mock_remove.assert_any_call(
            os.path.join("out", ".pdfimgextract-tmp-abc-001.png.part")
        )
        mock_remove.assert_any_call(os.path.join("out", ".pdfimgextract-tmp-123.part"))
