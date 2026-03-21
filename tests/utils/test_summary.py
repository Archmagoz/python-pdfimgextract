import pytest
from unittest.mock import MagicMock
from pdfimgextract.utils.summary import print_summary, _print_failed
from pdfimgextract.models.datamodels import ExtractionSummary, ExtractResult


class TestSummary:
    """
    Test suite for the reporting layer.
    Verifies terminal output and summary model generation.
    """

    @pytest.fixture
    def mock_failed_results(self):
        """A list of simulated failed extractions."""
        return [
            ExtractResult(
                ok=False,
                cancelled=False,
                xref=101,
                stem="001",
                ext=None,
                temp_path=None,
                error="Corrupt Stream",
            ),
            ExtractResult(
                ok=False,
                cancelled=False,
                xref=202,
                stem="002",
                ext=None,
                temp_path=None,
                error="Permission Denied",
            ),
        ]

    def test_print_failed_output(self, capsys, mock_failed_results):
        """Verify the formatting of the failed images list."""
        _print_failed(mock_failed_results)
        captured = capsys.readouterr()

        assert "image #001 (xref=101): Corrupt Stream" in captured.out
        assert "image #002 (xref=202): Permission Denied" in captured.out

    def test_print_summary_interrupted(self, capsys, mock_failed_results):
        """Verify the summary logic when the process is aborted via CTRL-C."""
        # Scenario: 10 total tasks, 5 processed (3 success, 2 fail), 5 remaining
        summary = print_summary(
            success_count=3,
            fail_count=2,
            failed=mock_failed_results,
            interrupted=True,
            results=[MagicMock()] * 5,
            total=10,
            out_dir="out",
        )

        captured = capsys.readouterr()

        # Check return object
        assert isinstance(summary, ExtractionSummary)
        assert summary.interrupted is True
        assert summary.success == 3

        # Check console output
        assert "3 images extracted before interruption" in captured.out
        assert "2 images failed" in captured.out
        assert "5 images not processed" in captured.out
        assert "image #001" in captured.out  # Ensure _print_failed was called

    def test_print_summary_normal_completion_with_failures(
        self, capsys, mock_failed_results
    ):
        """Verify report output for a finished run with some errors."""
        summary = print_summary(
            success_count=8,
            fail_count=2,
            failed=mock_failed_results,
            interrupted=False,
            results=[MagicMock()] * 10,
            total=10,
            out_dir="out_folder",
        )

        captured = capsys.readouterr()

        assert summary.interrupted is False
        assert "8 images extracted to out_folder" in captured.out
        assert "2 images failed" in captured.out

    def test_print_summary_perfect_run(self, capsys):
        """Verify report output when everything succeeds."""
        summary = print_summary(
            success_count=5,
            fail_count=0,
            failed=[],
            interrupted=False,
            results=[MagicMock()] * 5,
            total=5,
            out_dir="out",
        )

        captured = capsys.readouterr()

        assert "5 images extracted" in captured.out
        assert "failed" not in captured.out  # Should not print fail info
        assert summary.failed == 0
