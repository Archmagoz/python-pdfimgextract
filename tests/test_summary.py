from types import SimpleNamespace
from unittest.mock import patch

from pdfimgextract.summary import print_summary
from pdfimgextract.exit_codes import EXIT_SUCCESS, EXIT_FAILURE, EXIT_BY_USER


def make_result(stem="img", xref=1, error="err"):
    return SimpleNamespace(stem=stem, xref=xref, error=error)


@patch("builtins.print")
def test_interrupted_no_fail(mock_print):
    results = [make_result() for _ in range(2)]
    code = print_summary(
        success_count=2,
        fail_count=0,
        failed=[],
        interrupted=True,
        results=results,
        total=5,
        out_dir="out",
    )

    assert code == EXIT_BY_USER
    mock_print.assert_any_call("\x1b[33m2 images extracted before interruption\x1b[0m")
    mock_print.assert_any_call("\x1b[33m3 images were not processed\x1b[0m")
    mock_print.assert_any_call("\x1b[33mInterrupted by user (CTRL-C)\x1b[0m")


@patch("builtins.print")
def test_interrupted_with_fail(mock_print):
    results = [make_result() for _ in range(2)]
    failed = [make_result("fail1", 10, "error1"), make_result("fail2", 20, "error2")]

    code = print_summary(
        success_count=2,
        fail_count=2,
        failed=failed,
        interrupted=True,
        results=results,
        total=5,
        out_dir="out",
    )

    assert code == EXIT_BY_USER
    mock_print.assert_any_call("\x1b[33m2 images extracted before interruption\x1b[0m")
    mock_print.assert_any_call("\x1b[33m2 images failed to extract\x1b[0m")
    mock_print.assert_any_call("\x1b[33m- image #fail1 (xref=10): error1\x1b[0m")
    mock_print.assert_any_call("\x1b[33m- image #fail2 (xref=20): error2\x1b[0m")
    mock_print.assert_any_call("\x1b[33m3 images were not processed\x1b[0m")


@patch("builtins.print")
def test_not_interrupted_no_fail(mock_print):
    code = print_summary(
        success_count=5,
        fail_count=0,
        failed=[],
        interrupted=False,
        results=[make_result() for _ in range(5)],
        total=5,
        out_dir="out",
    )

    assert code == EXIT_SUCCESS
    mock_print.assert_any_call("\x1b[32m5 images successfully extracted to out\x1b[0m")


@patch("builtins.print")
def test_not_interrupted_with_fail(mock_print):
    failed = [make_result("fail", 1, "error")]

    code = print_summary(
        success_count=4,
        fail_count=1,
        failed=failed,
        interrupted=False,
        results=[make_result() for _ in range(5)],
        total=5,
        out_dir="out",
    )

    assert code == EXIT_FAILURE
    mock_print.assert_any_call("\x1b[32m4 images successfully extracted to out\x1b[0m")
    mock_print.assert_any_call("\x1b[33m1 images failed to extract\x1b[0m")
    mock_print.assert_any_call("\x1b[33m- image #fail (xref=1): error\x1b[0m")
