from unittest.mock import patch

from pdfimgextract.build_tasks import build_tasks, _build_extract_tasks
from pdfimgextract.datamodels import ExtractTask

# --- Tests for _build_extract_tasks ---


def test_build_extract_tasks_no_overwrite_skips_existing():
    """Verify that images are skipped when they exist and overwrite is False."""
    xrefs = [10, 20, 30]
    out_dir = "dummy_dir"
    run_id = "test-uuid"

    # Mocking load_existing_stems to say "1" and "2" already exist
    # Since we have 3 xrefs, digits will be 1, so stems are "1", "2", "3"
    with patch(
        "pdfimgextract.build_tasks.load_existing_stems", return_value={"1", "2"}
    ):
        tasks = _build_extract_tasks(xrefs, out_dir, run_id, overwrite=False)

        # Only xref 30 (stem "3") should be added to tasks
        assert len(tasks) == 1
        assert tasks[0].xref == 30
        assert tasks[0].stem == "3"


def test_build_extract_tasks_with_overwrite():
    """Verify that all tasks are created when overwrite is True."""
    xrefs = [10, 20]
    # If overwrite is True, load_existing_stems should not even be called
    with patch("pdfimgextract.build_tasks.load_existing_stems") as mock_load:
        tasks = _build_extract_tasks(xrefs, "dir", "id", overwrite=True)

        assert len(tasks) == 2
        mock_load.assert_not_called()


def test_build_extract_tasks_padding():
    """Verify zero-padding logic for stems (e.g., 01, 02... 10)."""
    xrefs = list(range(1, 11))  # 10 items, so digits = 2
    tasks = _build_extract_tasks(xrefs, "dir", "id", overwrite=True)

    assert tasks[0].stem == "01"
    assert tasks[-1].stem == "10"


def test_build_extract_tasks_empty_list():
    """Ensure it handles an empty xref list gracefully."""
    tasks = _build_extract_tasks([], "dir", "id", overwrite=False)
    assert tasks == []


# --- Tests for build_tasks (Main entry point) ---


@patch("pdfimgextract.build_tasks.scan_pdf_images")
@patch("fitz.open")
def test_build_tasks_integration(mock_fitz_open, mock_scan):
    """Test the orchestration from PDF path to Task list."""
    # Setup mocks
    mock_pdf_context = mock_fitz_open.return_value.__enter__.return_value
    mock_scan.return_value = ([100, 200], None, None)  # Mock xrefs, skip others

    pdf_path = "sample.pdf"
    out_dir = "out"

    tasks = build_tasks(pdf_path, out_dir, overwrite=True)

    # Assertions
    mock_fitz_open.assert_called_with(pdf_path)
    mock_scan.assert_called_once_with(mock_pdf_context)
    assert len(tasks) == 2
    assert isinstance(tasks[0], ExtractTask)
    assert tasks[0].xref == 100


def test_build_tasks_generates_uuid():
    """Ensure a run_id is generated if not provided."""
    with patch(
        "pdfimgextract.build_tasks.scan_pdf_images", return_value=([], None, None)
    ):
        with patch("fitz.open"):
            # We check if a UUID-like string is assigned to tasks (if any were created)
            # Or we can check the call to _build_extract_tasks
            with patch(
                "pdfimgextract.build_tasks._build_extract_tasks"
            ) as mock_internal:
                build_tasks("p.pdf", "out", run_id=None)
                called_run_id = mock_internal.call_args.kwargs["run_id"]
                assert len(called_run_id) == 36  # Standard UUID length
