import pytest
import uuid

from unittest.mock import patch, MagicMock

from pdfimgextract.core.build_tasks import build_tasks, _build_extract_tasks
from pdfimgextract.models.datamodels import Args


class TestBuildTasks:
    """
    Test suite for task generation logic.
    Ensures PDF scanning translates correctly into ExtractTask objects
    while respecting overwrite rules and existing files.
    """

    @pytest.fixture
    def mock_args(self):
        """Fixture for standard Args object."""
        return Args(
            pdf_path="test.pdf",
            out_dir="output/",
            workers=4,
            overwrite=False,
            dedup="xref",
        )

    def test_build_extract_tasks_no_overwrite(self):
        """
        Verify that images are skipped when they already exist
        and overwrite is set to False.
        """
        xrefs = [101, 102, 103]
        out_dir = "some_dir"
        run_id = "test-uuid"

        # Mocking load_existing_stems to simulate that "1" and "2" already exist
        # With 3 xrefs, digits will be 1, so stems are "1", "2", "3"
        with patch("pdfimgextract.core.build_tasks.load_existing_stems") as mock_load:
            mock_load.return_value = {"1", "2"}

            tasks = _build_extract_tasks(xrefs, out_dir, run_id, overwrite=False)

            # Should only have 1 task (the one for xref 103, stem "3")
            assert len(tasks) == 1
            assert tasks[0].xref == 103
            assert tasks[0].stem == "3"
            mock_load.assert_called_once_with(out_dir)

    def test_build_extract_tasks_with_overwrite(self):
        """
        Verify that all xrefs result in tasks when overwrite is True,
        even if files exist.
        """
        xrefs = [101, 102]
        with patch("pdfimgextract.core.build_tasks.load_existing_stems") as mock_load:
            tasks = _build_extract_tasks(xrefs, "dir", "id", overwrite=True)

            assert len(tasks) == 2
            # load_existing_stems should NOT be called if overwrite is True
            mock_load.assert_not_called()

    def test_build_extract_tasks_zfill_logic(self):
        """
        Check if stem strings are correctly padded with zeros based on total count.
        """
        # 10 xrefs means we need 2 digits (01, 02... 10)
        xrefs = list(range(10))
        tasks = _build_extract_tasks(xrefs, "dir", "id", overwrite=True)

        assert tasks[0].stem == "01"
        assert tasks[-1].stem == "10"

    def test_build_extract_tasks_empty_list(self):
        """Ensure the function handles empty xref lists gracefully."""
        tasks = _build_extract_tasks([], "dir", "id", overwrite=False)
        assert tasks == []

    @patch("pdfimgextract.core.build_tasks.fitz.open")
    @patch("pdfimgextract.core.build_tasks.scan_pdf_images")
    @patch("pdfimgextract.core.build_tasks.uuid.uuid4")
    def test_build_tasks_orchestration(
        self, mock_uuid, mock_scan, mock_fitz, mock_args
    ):
        """
        Test the main build_tasks function to ensure it opens the PDF,
        scans for images, and generates a run_id.
        """
        # Setup mocks
        mock_uuid.return_value = uuid.UUID("12345678-1234-5678-1234-567812345678")
        mock_scan.return_value = ([500], None, None)  # xrefs, names, types

        # Mock fitz context manager
        mock_pdf_instance = MagicMock()
        mock_fitz.return_value.__enter__.return_value = mock_pdf_instance

        tasks = build_tasks(mock_args)

        # Assertions
        mock_fitz.assert_called_once_with("test.pdf")
        mock_scan.assert_called_once_with(mock_pdf_instance, "xref")
        assert len(tasks) == 1
        assert tasks[0].run_id == str(mock_uuid.return_value)
        assert tasks[0].xref == 500

    @patch("pdfimgextract.core.build_tasks.print")
    def test_skipped_message_output(self, mock_print):
        """
        Verify that the warning messages are printed when files are skipped.
        This covers the 'if skipped:' branch.
        """
        # Force a skip by providing 1 xref and a matching existing stem
        with patch(
            "pdfimgextract.core.build_tasks.load_existing_stems", return_value={"1"}
        ):
            _build_extract_tasks([100], "dir", "id", overwrite=False)

            # Check if print was called (twice: one for the warning, one for the count)
            assert mock_print.call_count == 2
