import pytest

from unittest.mock import MagicMock, patch

from pdfimgextract.pool import run_pool, handle_interrupt
from pdfimgextract.worker import ExtractResult

# --- Fixtures ---


@pytest.fixture
def mock_args():
    args = MagicMock()
    args.workers = 4
    args.pdf_path = "test.pdf"
    args.out_dir = "out"
    return args


@pytest.fixture
def success_result():
    return ExtractResult(
        ok=True,
        cancelled=False,
        xref=1,
        stem="01",
        ext="png",
        temp_path="/tmp/1",
        error=None,
    )


# --- handle_interrupt Tests ---


def test_handle_interrupt_logic():
    """Verify pool termination and progress bar updates on interrupt."""
    mock_pool = MagicMock()
    mock_progress = MagicMock()
    mock_stop_event = MagicMock()

    handle_interrupt(mock_pool, mock_progress, mock_stop_event)

    mock_stop_event.set.assert_called_once()
    mock_pool.terminate.assert_called_once()
    mock_pool.join.assert_called_once()

    # Verify tqdm-specific updates
    mock_progress.set_description.assert_called()
    assert mock_progress.colour == "yellow"
    mock_progress.refresh.assert_called_once()


def test_handle_interrupt_none_safeguards():
    """Ensure no crashes if pool or progress are None (e.g., early interrupt)."""
    handle_interrupt(None, None, MagicMock())


# --- run_pool Tests ---


@patch("pdfimgextract.pool.Pool")
@patch("pdfimgextract.pool.finalize_result")
def test_run_pool_full_success(
    mock_finalize, mock_pool_class, mock_args, success_result
):
    """Test standard execution where all images are extracted correctly."""
    instance = mock_pool_class.return_value
    instance.imap_unordered.return_value = [success_result]

    # finalize_result returns (Result, commit_success_bool)
    mock_finalize.return_value = (success_result, True)

    mock_stop_event = MagicMock()
    mock_stop_event.is_set.return_value = False
    mock_progress = MagicMock()

    results, failed, success_count, interrupted = run_pool(
        [MagicMock()], mock_args, mock_stop_event, mock_progress
    )

    assert success_count == 1
    assert len(failed) == 0
    assert not interrupted
    assert results[0].ok is True
    instance.close.assert_called_once()


@patch("pdfimgextract.pool.Pool")
@patch("pdfimgextract.pool.remove_file_safely")
def test_run_pool_cancellation_path(
    mock_remove, mock_pool_class, mock_args, success_result
):
    """Test the branch where stop_event is set and temp files are cleaned up."""
    instance = mock_pool_class.return_value
    instance.imap_unordered.return_value = [success_result]

    mock_stop_event = MagicMock()
    mock_stop_event.is_set.return_value = True
    mock_progress = MagicMock()

    results, failed, success_count, interrupted = run_pool(
        [MagicMock()], mock_args, mock_stop_event, mock_progress
    )

    # Verify logic for the 'cancelled' ExtractResult instantiation
    assert results[0].cancelled is True
    assert results[0].ok is False
    assert results[0].temp_path is None
    assert success_count == 0

    # Verify cleanup of the original temp file
    mock_remove.assert_called_with(success_result.temp_path)


@patch("pdfimgextract.pool.Pool")
@patch("pdfimgextract.pool.finalize_result")
def test_run_pool_worker_error_branch(mock_finalize, mock_pool_class, mock_args):
    """Test tracking of failed (but not cancelled) worker tasks."""
    err_result = ExtractResult(
        ok=False,
        cancelled=False,
        xref=5,
        stem="5",
        ext=None,
        temp_path=None,
        error="Corrupt",
    )

    instance = mock_pool_class.return_value
    instance.imap_unordered.return_value = [err_result]
    mock_finalize.return_value = (err_result, False)

    mock_stop_event = MagicMock()
    mock_stop_event.is_set.return_value = False

    results, failed, success_count, interrupted = run_pool(
        [MagicMock()], mock_args, mock_stop_event, MagicMock()
    )

    assert len(failed) == 1
    assert success_count == 0
    assert failed[0].error == "Corrupt"


@patch("pdfimgextract.pool.Pool")
@patch("pdfimgextract.pool.handle_interrupt")
def test_run_pool_keyboard_interrupt_catch(mock_handle, mock_pool_class, mock_args):
    """Ensure KeyboardInterrupt inside the loop triggers the handler."""
    instance = mock_pool_class.return_value
    instance.imap_unordered.side_effect = KeyboardInterrupt()

    results, failed, success_count, interrupted = run_pool(
        [MagicMock()], mock_args, MagicMock(), MagicMock()
    )

    assert interrupted is True
    mock_handle.assert_called_once()
