import pytest
import hashlib

from unittest.mock import MagicMock, patch
from pdfimgextract.dedup import (
    load_existing_stems,
    _compute_stream_hash,
    scan_pdf_images,
)

# --- load_existing_stems (3 lines) ---


def test_load_existing_stems_full(tmp_path):
    """Cover the 'if not os.path.isdir' and the splitext loop."""
    # 1. Missing dir branch
    assert load_existing_stems(str(tmp_path / "missing")) == set()

    # 2. Success branch
    (tmp_path / "001.png").write_text("")
    (tmp_path / "002.jpg").write_text("")
    stems = load_existing_stems(str(tmp_path))
    assert stems == {"001", "002"}


# --- _compute_stream_hash (3 lines) ---


def test_compute_stream_hash_branches():
    """Cover both return None and return digest."""
    pdf = MagicMock()
    # Case: None
    pdf.xref_stream.return_value = None
    assert _compute_stream_hash(pdf, 1) is None

    # Case: Valid
    pdf.xref_stream.return_value = b"data"
    expected = hashlib.sha256(b"data").digest()
    assert _compute_stream_hash(pdf, 2) == expected


# --- scan_pdf_images (Remaining 7+ lines) ---


@patch("pdfimgextract.dedup.create_progress_bar")
@patch("pdfimgextract.dedup.update_scan_stats")
@patch("pdfimgextract.dedup.scanning_complete")
def test_scan_pdf_images_xref_full_path(mock_complete, mock_stats, mock_pb):
    """Cover the 'if dedup.lower() == "xref"' block and final returns."""
    pdf = MagicMock()
    pdf.__len__.return_value = 1
    page = MagicMock()
    page.get_images.return_value = [[10], [10]]  # One unique, one duplicate XREF
    pdf.__iter__.return_value = [page]

    xrefs, unique, dups = scan_pdf_images(pdf, "XREF")

    assert xrefs == [10]
    assert unique == 1
    mock_complete.assert_called()
    # Note: In XREF mode, the code returns early, so update_scan_stats is NOT called.


@patch("pdfimgextract.dedup.create_progress_bar")
@patch("pdfimgextract.dedup._compute_stream_hash")
@patch("pdfimgextract.dedup.update_scan_stats")
@patch("pdfimgextract.dedup.scanning_complete")
def test_scan_pdf_images_hash_full_path(mock_complete, mock_stats, mock_hash, mock_pb):
    """
    Cover all branches of the 'if dedup.lower() == "hash"' block:
    - xref in seen_xref (continue)
    - xref not in hash_cache (compute)
    - img_hash and img_hash in seen_hashes (continue)
    - img_hash (seen_hashes.add)
    - final stats and progress closing
    """
    pdf = MagicMock()
    pdf.__len__.return_value = 1
    page = MagicMock()
    # Sequence:
    # 1. XREF 10 (Hash A) -> New
    # 2. XREF 10 (Same XREF) -> Trigger 'if xref in seen_xref'
    # 3. XREF 20 (Hash A) -> Trigger 'if img_hash and img_hash in seen_hashes'
    # 4. XREF 30 (Hash B) -> New
    page.get_images.return_value = [[10], [10], [20], [30]]
    pdf.__iter__.return_value = [page]

    # Only called for 10, 20, 30. 10(2nd) is skipped by xref check.
    mock_hash.side_effect = [b"A", b"A", b"B"]

    xrefs, unique, dups = scan_pdf_images(pdf, "hash")

    assert xrefs == [10, 30]
    assert dups == 2
    assert unique == 2

    # Verify the hash_cache was used: mock_hash should only be called once for XREF 10
    # even though it appears twice in get_images.
    assert mock_hash.call_count == 3

    # Verify stats and completion calls
    mock_stats.assert_called()
    mock_complete.assert_called()


@patch("pdfimgextract.dedup.create_progress_bar")
@patch("pdfimgextract.dedup.finish_progress_bar")
def test_scan_pdf_interrupt_handling(mock_finish, mock_pb):
    """Cover the KeyboardInterrupt branch explicitly."""
    pdf = MagicMock()
    pdf.__iter__.side_effect = KeyboardInterrupt()

    # Case: progress is not None
    mock_bar = MagicMock()
    mock_pb.return_value = mock_bar

    with pytest.raises(KeyboardInterrupt):
        scan_pdf_images(pdf, "hash")

    mock_finish.assert_called_with(mock_bar, cancelled=True)

    # Case: progress IS None (for completeness)
    mock_pb.return_value = None
    with pytest.raises(KeyboardInterrupt):
        scan_pdf_images(pdf, "hash")
