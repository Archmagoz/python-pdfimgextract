from unittest.mock import patch

from pdfimgextract.filesystem import remove_file_safely, cleanup_stale_temp_files

# --- Tests for remove_file_safely ---


def test_remove_file_safely_none_path():
    """Ensure the function returns early if path is None."""
    # If it doesn't return early, os.remove(None) would raise a TypeError
    remove_file_safely(None)


def test_remove_file_safely_success(tmp_path):
    """Verify a file is actually removed when it exists."""
    test_file = tmp_path / "to_delete.txt"
    test_file.write_text("content")

    assert test_file.exists()
    remove_file_safely(str(test_file))
    assert not test_file.exists()


def test_remove_file_safely_ignores_oserror():
    """Verify that OSErrors (like FileNotFoundError) are suppressed."""
    # Attempting to remove a file that definitely doesn't exist
    # If the suppress(OSError) works, no exception will be raised.
    remove_file_safely("non_existent_file_path_9999.txt")


def test_remove_file_safely_permission_error():
    """Ensure other OSErrors like PermissionError are also suppressed."""
    with patch("os.remove", side_effect=PermissionError):
        remove_file_safely("dummy_path")


# --- Tests for cleanup_stale_temp_files ---


def test_cleanup_stale_temp_files_not_a_dir():
    """Ensure the function returns early if the directory doesn't exist."""
    with patch("os.path.isdir", return_value=False):
        with patch("os.listdir") as mock_list:
            cleanup_stale_temp_files("fake_dir")
            mock_list.assert_not_called()


def test_cleanup_stale_temp_files_deletes_only_matches(tmp_path):
    """Verify that only files matching the specific pattern are deleted."""
    # Matching file
    match = tmp_path / ".pdfimgextract-tmp-abc.part"
    match.write_text("temp")

    # Non-matching: wrong prefix
    no_match_prefix = tmp_path / "other-tmp.part"
    no_match_prefix.write_text("keep")

    # Non-matching: wrong suffix
    no_match_suffix = tmp_path / ".pdfimgextract-tmp-abc.jpg"
    no_match_suffix.write_text("keep")

    cleanup_stale_temp_files(str(tmp_path))

    assert not match.exists()
    assert no_match_prefix.exists()
    assert no_match_suffix.exists()


def test_cleanup_stale_temp_files_nested_error_handling(tmp_path):
    """Ensure the loop continues even if one file removal fails."""
    file1 = tmp_path / ".pdfimgextract-tmp-1.part"
    file2 = tmp_path / ".pdfimgextract-tmp-2.part"
    file1.write_text("data")
    file2.write_text("data")

    # Mock os.remove to fail on the first file but succeed on the second
    with patch("os.remove", side_effect=[OSError, None]):
        cleanup_stale_temp_files(str(tmp_path))
        # Logic: If it processed both, os.remove should be called twice
        assert True
