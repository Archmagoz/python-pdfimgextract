from unittest.mock import patch, MagicMock
from pdfimgextract.summary import print_summary, _print_failed

from pdfimgextract.datamodels import ExtractResult

# --- Helper ---


def create_mock_result(stem="01", xref=100, error="some error"):
    return ExtractResult(
        ok=False,
        cancelled=False,
        xref=xref,
        stem=stem,
        ext="png",
        temp_path=None,
        error=error,
    )


# --- Tests ---


def test_print_failed_output():
    """Verify that _print_failed iterates through the failed list and prints."""
    failed_list = [
        create_mock_result("01", 100, "Corrupt stream"),
        create_mock_result("02", 200, "Missing data"),
    ]

    with patch("builtins.print") as mock_print:
        _print_failed(failed_list)
        # Check if it was called for each item
        assert mock_print.call_count == 2
        # Verify a snippet of the message
        msg = mock_print.call_args_list[0][0][0]
        assert "image #01" in msg
        assert "xref=100" in msg


def test_print_summary_interrupted_with_failures_and_remaining():
    """Covers: interrupted=True, fail_count > 0, and remaining > 0."""
    failed_item = create_mock_result()

    # total=10, results length=5 -> remaining=5
    results = [MagicMock()] * 5

    with patch("builtins.print") as mock_print:
        summary = print_summary(
            success_count=4,
            fail_count=1,
            failed=[failed_item],
            interrupted=True,
            results=results,
            total=10,
            out_dir="out",
        )

        assert summary.interrupted is True
        assert summary.success == 4
        assert summary.failed == 1
        # Check for "remaining" print
        any_remaining_msg = any(
            "5 images not processed" in str(call) for call in mock_print.call_args_list
        )
        assert any_remaining_msg


def test_print_summary_interrupted_minimal():
    """Covers: interrupted=True but no failures and no remaining."""
    results = [MagicMock()] * 5

    summary = print_summary(
        success_count=5,
        fail_count=0,
        failed=[],
        interrupted=True,
        results=results,
        total=5,  # 5 tasks, 5 results -> remaining=0
        out_dir="out",
    )
    assert summary.interrupted is True
    assert summary.failed == 0


def test_print_summary_normal_completion_with_success():
    """Covers: interrupted=False and success_count > 0."""
    with patch("builtins.print") as mock_print:
        summary = print_summary(
            success_count=10,
            fail_count=0,
            failed=[],
            interrupted=False,
            results=[MagicMock()] * 10,
            total=10,
            out_dir="out",
        )

        assert summary.interrupted is False
        assert summary.success == 10
        # Verify success message printed
        any_success_msg = any(
            "10 images extracted" in str(call) for call in mock_print.call_args_list
        )
        assert any_success_msg


def test_print_summary_normal_completion_only_failures():
    """Covers: interrupted=False, success_count=0, fail_count > 0."""
    failed_item = create_mock_result()

    with patch("builtins.print") as mock_print:
        summary = print_summary(
            success_count=0,
            fail_count=1,
            failed=[failed_item],
            interrupted=False,
            results=[MagicMock()],
            total=1,
            out_dir="out",
        )

        assert summary.success == 0
        assert summary.failed == 1
        # Verify failed details were printed
        assert mock_print.call_count >= 2  # Summary line + detail line
