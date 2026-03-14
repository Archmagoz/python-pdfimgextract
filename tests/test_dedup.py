import pytest

from unittest.mock import patch, MagicMock
from pdfimgextract.dedup import (
    load_existing_stems,
    _image_signature,
    _compute_stream_hash,
    scan_pdf_images,
)

# --- Tests for load_existing_stems ---


def test_load_existing_stems_dir_not_exists():
    """Branch: if not os.path.isdir(out_dir)"""
    with patch("os.path.isdir", return_value=False):
        assert load_existing_stems("fake_path") == set()


def test_load_existing_stems_success(tmp_path):
    """Branch: Success loop and splitext logic."""
    (tmp_path / "01.png").write_text("")
    (tmp_path / "02.jpg").write_text("")
    (tmp_path / "other.txt").write_text("")

    stems = load_existing_stems(str(tmp_path))
    assert stems == {"01", "02", "other"}


# --- Tests for _image_signature ---


def test_image_signature():
    """Verify metadata extraction from the fitz image tuple."""
    # Tuple index: 0=xref, 1=smask, 2=width, 3=height, 4=bpc, 5=colorspace
    mock_img = (100, 0, 1920, 1080, 8, "DeviceRGB")
    expected = (1920, 1080, 8, "DeviceRGB")
    assert _image_signature(mock_img) == expected


# --- Tests for _compute_stream_hash ---


def test_compute_stream_hash_none():
    """Branch: if stream is None"""
    mock_pdf = MagicMock()
    mock_pdf.xref_stream.return_value = None
    assert _compute_stream_hash(mock_pdf, 100) is None


def test_compute_stream_hash_success():
    """Verify hash computation from bytes."""
    mock_pdf = MagicMock()
    mock_pdf.xref_stream.return_value = b"image_data"
    result = _compute_stream_hash(mock_pdf, 100)
    assert result is not None
    assert len(result) == 32  # SHA256 digest length


# --- Tests for scan_pdf_images ---


@patch("pdfimgextract.dedup.create_progress_bar")
@patch("pdfimgextract.dedup.update_scan_stats")
@patch("pdfimgextract.dedup.scanning_complete")
def test_scan_pdf_images_deduplication_logic(mock_complete, mock_stats, mock_pb):
    """Test all three layers of deduplication (xref, signature, hash)."""
    mock_pdf = MagicMock()
    mock_pb_instance = MagicMock()
    mock_pb.return_value = mock_pb_instance

    # Simulate 1 page with 4 images
    # 1. Unique image
    # 2. Duplicate xref
    # 3. Same signature, same hash (duplicate)
    # 4. Same signature, different hash (unique)

    img1 = (10, 0, 100, 100, 8, "RGB")
    img2 = (10, 0, 100, 100, 8, "RGB")  # Same xref
    img3 = (20, 0, 100, 100, 8, "RGB")  # Same signature as img1
    img4 = (30, 0, 100, 100, 8, "RGB")  # Same signature as img1

    mock_page = MagicMock()
    mock_page.get_images.return_value = [img1, img2, img3, img4]
    mock_pdf.__iter__.return_value = [mock_page]
    mock_pdf.__len__.return_value = 1

    # Mock hash returns:
    # img3 returns same hash as img1. img4 returns unique hash.
    # Note: _compute_stream_hash is called when signature is seen.
    with patch("pdfimgextract.dedup._compute_stream_hash") as mock_hash:
        mock_hash.side_effect = [
            b"hash_a",  # img1 first call
            b"hash_a",  # img3 check (duplicate)
            b"hash_b",  # img4 check (unique)
        ]

        xrefs, unique, dups = scan_pdf_images(mock_pdf)

        assert xrefs == [10, 30]
        assert unique == 2
        assert dups == 2  # 1 from xref, 1 from hash


@patch("pdfimgextract.dedup.create_progress_bar")
@patch("pdfimgextract.dedup.finish_progress_bar")
def test_scan_pdf_images_keyboard_interrupt(mock_finish, mock_pb):
    """Branch: except KeyboardInterrupt"""
    mock_pdf = MagicMock()
    mock_pdf.__iter__.side_effect = KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        scan_pdf_images(mock_pdf)

    mock_finish.assert_called_once()


@patch("pdfimgextract.dedup.create_progress_bar")
def test_scan_pdf_images_handle_none_hash(mock_pb):
    """Ensure logic continues if _compute_stream_hash returns None."""
    mock_pdf = MagicMock()
    img = (10, 0, 100, 100, 8, "RGB")
    mock_page = MagicMock()
    mock_page.get_images.return_value = [img]
    mock_pdf.__iter__.return_value = [mock_page]

    with patch("pdfimgextract.dedup._compute_stream_hash", return_value=None):
        xrefs, unique, dups = scan_pdf_images(mock_pdf)
        assert unique == 1
        assert len(xrefs) == 1


# --- Additional Tests for scan_pdf_images ---


@patch("pdfimgextract.dedup.create_progress_bar")
@patch("pdfimgextract.dedup.scanning_complete")
def test_scan_pdf_images_skip_dedup_branch(mock_complete, mock_pb):
    """Branch: if skip_dedup: Verify fast-path without deduplication logic."""
    mock_pdf = MagicMock()
    mock_pb_instance = MagicMock()
    mock_pb.return_value = mock_pb_instance

    # 3 images, including a duplicate xref (10)
    img1 = (10, 0, 100, 100, 8, "RGB")
    img2 = (10, 0, 100, 100, 8, "RGB")
    img3 = (20, 0, 200, 200, 8, "RGB")

    mock_page = MagicMock()
    mock_page.get_images.return_value = [img1, img2, img3]
    mock_pdf.__iter__.return_value = [mock_page]
    mock_pdf.__len__.return_value = 1

    # In skip_dedup mode, all xrefs should be collected regardless of duplicates
    xrefs, unique, dups = scan_pdf_images(mock_pdf, skip_dedup=True)

    assert xrefs == [10, 10, 20]
    assert unique == 3
    assert dups == 0
    mock_complete.assert_called_once()


@patch("pdfimgextract.dedup.create_progress_bar")
def test_scan_pdf_images_empty_pdf(mock_pb):
    """Verify behavior when the PDF has no pages or no images."""
    mock_pdf = MagicMock()
    mock_pdf.__iter__.return_value = []
    mock_pdf.__len__.return_value = 0

    xrefs, unique, dups = scan_pdf_images(mock_pdf)

    assert xrefs == []
    assert unique == 0
    assert dups == 0


@patch("pdfimgextract.dedup.create_progress_bar")
@patch("pdfimgextract.dedup._compute_stream_hash")
def test_scan_pdf_images_signature_collision_and_hash_storage(mock_hash, mock_pb):
    """
    Test the specific branch where a signature is seen for the first time.
    Ensures that img_hash is computed and added to seen_hashes even
    if no collision occurred.
    """
    mock_pdf = MagicMock()
    img1 = (50, 0, 300, 300, 8, "CMYK")

    mock_page = MagicMock()
    mock_page.get_images.return_value = [img1]
    mock_pdf.__iter__.return_value = [mock_page]
    mock_pdf.__len__.return_value = 1

    mock_hash.return_value = b"unique_hash_z"

    xrefs, unique, dups = scan_pdf_images(mock_pdf)

    # Verify xref was added
    assert xrefs == [50]
    # Verify hash was actually computed for the new signature
    mock_hash.assert_called_with(mock_pdf, 50)


@patch("pdfimgextract.dedup.create_progress_bar")
def test_scan_pdf_images_multiple_pages(mock_pb):
    """Ensure images are collected across multiple PDF pages."""
    mock_pdf = MagicMock()

    mock_pdf.xref_stream.return_value = b"dummy_data"

    img_p1 = (1, 0, 10, 10, 8, "Gray")
    img_p2 = (2, 0, 20, 20, 8, "Gray")

    mock_page1 = MagicMock()
    mock_page1.get_images.return_value = [img_p1]
    mock_page2 = MagicMock()
    mock_page2.get_images.return_value = [img_p2]

    mock_pdf.__iter__.return_value = [mock_page1, mock_page2]
    mock_pdf.__len__.return_value = 2

    xrefs, unique, dups = scan_pdf_images(mock_pdf)

    assert len(xrefs) == 2
    assert 1 in xrefs
    assert 2 in xrefs
