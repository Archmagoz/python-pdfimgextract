import uuid

from unittest.mock import patch, MagicMock
from pdfimgextract.build_tasks import build_tasks, _build_extract_tasks
from pdfimgextract.datamodels import Args

# --- Success Path & Logic Tests ---


def test_build_extract_tasks_basic():
    """Test task creation with zero padding and no existing files."""
    xrefs = [10, 20, 30]
    out_dir = "/tmp/out"
    run_id = "test-run"

    # Mock load_existing_stems to return empty (nothing to skip)
    with patch("pdfimgextract.build_tasks.load_existing_stems", return_value=set()):
        tasks = _build_extract_tasks(xrefs, out_dir, run_id, overwrite=False)

    assert len(tasks) == 3
    # Check padding: 3 items means digits=1, so no leading zeros
    assert tasks[0].stem == "1"
    assert tasks[0].xref == 10
    assert tasks[2].stem == "3"


def test_build_extract_tasks_padding():
    """Test that padding works correctly for 10+ items (01, 02...)."""
    xrefs = list(range(10, 21))  # 11 items
    with patch("pdfimgextract.build_tasks.load_existing_stems", return_value=set()):
        tasks = _build_extract_tasks(xrefs, "out", "id", False)

    assert tasks[0].stem == "01"
    assert tasks[-1].stem == "11"


def test_build_extract_tasks_skipping(capsys):
    """Test skipping logic when overwrite is False and files exist."""
    xrefs = [100, 200, 300]
    # Simulate that "1" and "2" already exist in the folder
    existing = {"1", "2"}

    with patch("pdfimgextract.build_tasks.load_existing_stems", return_value=existing):
        tasks = _build_extract_tasks(xrefs, "out", "id", overwrite=False)

    # Should only create task for "3"
    assert len(tasks) == 1
    assert tasks[0].stem == "3"

    # Verify the warning message was printed to stdout
    captured = capsys.readouterr()
    assert "Skipping 2 existing files" in captured.out


def test_build_extract_tasks_overwrite_enabled(capsys):
    """Test that overwrite=True ignores existing files and prints nothing."""
    xrefs = [100, 200]
    existing = {"1", "2"}

    # Even if files exist, if overwrite is True, we don't load them and don't skip
    with patch("pdfimgextract.build_tasks.load_existing_stems") as mock_load:
        tasks = _build_extract_tasks(xrefs, "out", "id", overwrite=True)
        mock_load.assert_not_called()

    assert len(tasks) == 2
    captured = capsys.readouterr()
    assert "Skipping" not in captured.out


def test_build_extract_tasks_empty_list():
    """Ensure it handles an empty list of xrefs gracefully."""
    tasks = _build_extract_tasks([], "out", "id", False)
    assert tasks == []


# --- Integration / Wrapper Tests ---


@patch("pdfimgextract.build_tasks.fitz.open")
@patch("pdfimgextract.build_tasks.scan_pdf_images")
def test_build_tasks_wrapper(mock_scan, mock_fitz, tmp_path):
    """Test the public build_tasks function and UUID generation."""
    # Setup mocks
    mock_pdf = MagicMock()
    mock_fitz.return_value.__enter__.return_value = mock_pdf
    # scan_pdf_images returns (xrefs, images_info, stats)
    mock_scan.return_value = ([55, 66], None, None)

    args = Args(
        pdf_path="test.pdf",
        out_dir=str(tmp_path),
        workers=4,
        overwrite=False,
        dedup="xref",
    )

    # 1. Test with explicit run_id
    tasks = build_tasks(args, run_id="manual-id")
    assert len(tasks) == 2
    assert tasks[0].run_id == "manual-id"

    # 2. Test with generated run_id (uuid4)
    tasks_auto = build_tasks(args)
    assert len(tasks_auto) == 2
    # Check if it's a valid UUID string
    val = uuid.UUID(tasks_auto[0].run_id, version=4)
    assert str(val) == tasks_auto[0].run_id
