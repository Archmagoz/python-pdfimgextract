from unittest.mock import patch, MagicMock

from pdfimgextract.pool import handle_interrupt, run_pool
from pdfimgextract.datamodels import ExtractResult

# --- Tests for handle_interrupt ---


def test_handle_interrupt_with_progress():
    """Verify stop_event is set and progress bar is updated/coloured."""
    mock_pool = MagicMock()
    mock_progress = MagicMock()
    mock_stop_event = MagicMock()

    handle_interrupt(mock_pool, mock_progress, mock_stop_event)

    mock_stop_event.set.assert_called_once()
    assert mock_progress.colour == "yellow"
    mock_pool.terminate.assert_called_once()
    mock_pool.join.assert_called_once()


def test_handle_interrupt_none_checks():
    """Ensure handle_interrupt doesn't crash if pool or progress is None."""
    mock_stop_event = MagicMock()
    # This should simply run without raising AttributeError
    handle_interrupt(None, None, mock_stop_event)
    mock_stop_event.set.assert_called_once()


# --- Tests for run_pool ---


@patch("pdfimgextract.pool.Pool")
@patch("pdfimgextract.pool.finalize_result")
def test_run_pool_success(mock_finalize, mock_pool_class):
    """Cover the main loop, successful results, and pool lifecycle."""
    # Setup Pool Mock
    mock_pool_instance = MagicMock()
    mock_pool_class.return_value = mock_pool_instance

    # Setup task results
    res1 = ExtractResult(
        ok=True,
        cancelled=False,
        xref=1,
        stem="1",
        ext="png",
        temp_path="t1",
        error=None,
    )
    res2 = ExtractResult(
        ok=False,
        cancelled=False,
        xref=2,
        stem="2",
        ext="png",
        temp_path="t2",
        error=None,
    )

    mock_pool_instance.imap_unordered.return_value = [res1, res2]
    mock_finalize.side_effect = [(res1, "path1"), (res2, None)]

    mock_progress = MagicMock()
    mock_stop_event = MagicMock()
    mock_stop_event.is_set.return_value = False

    results, failed, success, interrupted = run_pool(
        tasks=[MagicMock(), MagicMock()],
        workers=2,
        pdf_path="in.pdf",
        stop_event=mock_stop_event,
        progress=mock_progress,
        out_dir="out",
    )

    assert len(results) == 2
    assert len(failed) == 1
    assert success == 1
    assert interrupted is False
    mock_pool_instance.close.assert_called_once()


@patch("pdfimgextract.pool.Pool")
@patch("pdfimgextract.pool.remove_file_safely")
def test_run_pool_cancellation_logic(mock_remove, mock_pool_class):
    """Cover the stop_event.is_set() branch inside the loop."""
    mock_pool_instance = MagicMock()
    mock_pool_class.return_value = mock_pool_instance

    raw_res = ExtractResult(
        ok=True,
        cancelled=False,
        xref=1,
        stem="1",
        ext="png",
        temp_path="t1",
        error=None,
    )
    mock_pool_instance.imap_unordered.return_value = [raw_res]

    mock_stop_event = MagicMock()
    mock_stop_event.is_set.return_value = True  # Force cancellation branch

    results, failed, success, interrupted = run_pool(
        tasks=[MagicMock()],
        workers=1,
        pdf_path="p.pdf",
        stop_event=mock_stop_event,
        progress=MagicMock(),
        out_dir="out",
    )

    assert results[0].cancelled is True
    assert results[0].temp_path is None
    mock_remove.assert_called_once_with("t1")


@patch("pdfimgextract.pool.Pool")
@patch("pdfimgextract.pool.handle_interrupt")
def test_run_pool_keyboard_interrupt(mock_handle, mock_pool_class):
    """Cover the 'except KeyboardInterrupt' block."""
    mock_pool_instance = MagicMock()
    mock_pool_class.return_value = mock_pool_instance

    # Force interrupt when iterating imap_unordered
    mock_pool_instance.imap_unordered.side_effect = KeyboardInterrupt

    results, failed, success, interrupted = run_pool(
        tasks=[MagicMock()],
        workers=1,
        pdf_path="p.pdf",
        stop_event=MagicMock(),
        progress=MagicMock(),
        out_dir="out",
    )

    assert interrupted is True
    mock_handle.assert_called_once()
