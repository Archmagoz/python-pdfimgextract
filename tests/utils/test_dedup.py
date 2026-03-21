import pytest

from unittest.mock import patch, MagicMock

from pdfimgextract.utils.dedup import scan_pdf_images, _compute_stream_hash


class TestDedupUtils:
    """
    Test suite for PDF image scanning and deduplication logic.
    Ensures both XREF and Hash-based filtering work as expected.
    """

    def test_compute_stream_hash_success(self):
        """Verify SHA256 hashing of a valid PDF stream."""
        mock_pdf = MagicMock()
        mock_pdf.xref_stream.return_value = b"image_data_123"

        result = _compute_stream_hash(mock_pdf, 10)

        assert result is not None
        assert isinstance(result, bytes)
        # Verify it's a 32-byte SHA256 digest
        assert len(result) == 32

    def test_compute_stream_hash_none(self):
        """Verify None is returned if the stream cannot be read."""
        mock_pdf = MagicMock()
        mock_pdf.xref_stream.return_value = None

        assert _compute_stream_hash(mock_pdf, 10) is None

    @patch("pdfimgextract.utils.dedup.create_progress_bar")
    @patch("pdfimgextract.utils.dedup.update_scan_stats")
    @patch("pdfimgextract.utils.dedup.scanning_complete")
    def test_scan_xref_mode(self, mock_complete, mock_stats, mock_pb):
        """Tests deduplication using XREF identifiers (identical objects)."""
        # Mock PDF with 1 page containing 2 images (one duplicate XREF)
        mock_page = MagicMock()
        # image tuple format: (xref, smask, width, height, bpc, colorspace, ...)
        mock_page.get_images.return_value = [(10, 0), (10, 0), (20, 0)]

        mock_pdf = MagicMock()
        mock_pdf.__len__.return_value = 1
        mock_pdf.__iter__.return_value = [mock_page]

        xrefs, unique, dups = scan_pdf_images(mock_pdf, "xref")

        assert xrefs == [10, 20]
        assert unique == 2
        assert dups == 1
        mock_complete.assert_called_once()

    @patch("pdfimgextract.utils.dedup._compute_stream_hash")
    @patch("pdfimgextract.utils.dedup.create_progress_bar")
    @patch("pdfimgextract.utils.dedup.scanning_complete")
    def test_scan_hash_mode(self, mock_complete, mock_pb, mock_hash):
        """Tests deduplication using image content hashing."""
        mock_page = MagicMock()
        # Two different XREFs, but we will make them have the same hash
        mock_page.get_images.return_value = [(10, 0), (20, 0)]

        mock_pdf = MagicMock()
        mock_pdf.__len__.return_value = 1
        mock_pdf.__iter__.return_value = [mock_page]

        # Both XREFs return the same content hash
        mock_hash.return_value = b"same_hash_value"

        xrefs, unique, dups = scan_pdf_images(mock_pdf, "hash")

        assert xrefs == [10]  # Only the first one is unique by hash
        assert unique == 1
        assert dups == 1

    @patch("pdfimgextract.utils.dedup._compute_stream_hash")
    @patch("pdfimgextract.utils.dedup.create_progress_bar")
    def test_scan_hash_mode_xref_short_circuit(self, mock_pb, mock_hash):
        """Verify hash mode skips hashing if XREF is already seen."""
        mock_page = MagicMock()
        mock_page.get_images.return_value = [(10, 0), (10, 0)]

        mock_pdf = MagicMock()
        mock_pdf.__len__.return_value = 1
        mock_pdf.__iter__.return_value = [mock_page]

        scan_pdf_images(mock_pdf, "hash")

        # Hash should only be computed once for XREF 10
        assert mock_hash.call_count == 1

    @patch("pdfimgextract.utils.dedup.create_progress_bar")
    @patch("pdfimgextract.utils.dedup.finish_progress_bar")
    def test_scan_keyboard_interrupt(self, mock_finish, mock_pb):
        """Verify progress bar cleanup on CTRL-C during scan."""
        mock_pdf = MagicMock()
        mock_pdf.__len__.return_value = 1
        # Force interrupt during iteration
        mock_pdf.__iter__.side_effect = KeyboardInterrupt()

        with pytest.raises(KeyboardInterrupt):
            scan_pdf_images(mock_pdf, "xref")

        mock_finish.assert_called_once_with(mock_pb.return_value, cancelled=True)
