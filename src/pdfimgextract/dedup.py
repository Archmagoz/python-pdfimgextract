import hashlib
import fitz
import os

from contextlib import suppress

from pdfimgextract.progress_bar import (
    create_progress_bar,
    update_scan_stats,
    scanning_complete,
    finish_progress_bar,
)


def load_existing_stems(out_dir: str) -> set[str]:
    """
    Collect existing file stems from the destination folder.
    Used to avoid recreating files when overwrite is disabled.
    """
    stems: set[str] = set()

    if not os.path.isdir(out_dir):
        return stems

    for name in os.listdir(out_dir):
        stem, _ = os.path.splitext(name)
        stems.add(stem)

    return stems


def _image_signature(img: tuple) -> tuple:
    """
    Build a fast metadata signature for an image.
    This signature is used as a quick pre-check before computing
    a full hash of the image stream.
    """
    width, height, bpc, colorspace = img[2], img[3], img[4], img[5]
    return (width, height, bpc, colorspace)


def _compute_stream_hash(pdf: fitz.Document, xref: int) -> bytes | None:
    """
    Compute a SHA256 hash from the raw image stream.
    Returns None if the stream cannot be read.
    """
    stream = pdf.xref_stream(xref)
    if stream is None:
        return None
    return hashlib.sha256(stream).digest()


def scan_pdf_images(
    pdf: fitz.Document, dedup: bool = False
) -> tuple[list[int], int, int]:
    """
    Scan the PDF and return a list of unique image xrefs.
    Deduplication is performed using:
      1. xref check (fast)
      2. metadata signature
      3. stream hash (slow but accurate)
    """

    seen_xref: set[int] = set()
    seen_signatures: set[tuple] = set()
    seen_hashes: set[bytes] = set()
    xrefs: list[int] = []

    unique_images = 0
    duplicates = 0

    progress = create_progress_bar(total=len(pdf), desc="Scanning PDF", unit="page")

    try:
        if not dedup:
            for page in pdf:
                for img in page.get_images(full=True):
                    xref = img[0]
                    xrefs.append(xref)
                progress.update(1)
            scanning_complete(progress)
            progress.close()
            return xrefs, len(xrefs), 0

        else:
            for page in pdf:
                for img in page.get_images(full=True):
                    xref = img[0]

                    if xref in seen_xref:
                        duplicates += 1
                        continue
                    seen_xref.add(xref)

                    signature = _image_signature(img)
                    img_hash = None

                    if signature in seen_signatures:
                        img_hash = _compute_stream_hash(pdf, xref)
                        if img_hash and img_hash in seen_hashes:
                            duplicates += 1
                            continue

                    xrefs.append(xref)
                    unique_images += 1
                    seen_signatures.add(signature)

                    if img_hash is None:
                        img_hash = _compute_stream_hash(pdf, xref)
                    if img_hash:
                        seen_hashes.add(img_hash)

                progress.update(1)
                update_scan_stats(progress, unique_images, duplicates)

    except KeyboardInterrupt:
        if progress is not None:
            with suppress(Exception):
                finish_progress_bar(progress, cancelled=True)
        raise

    scanning_complete(progress)
    progress.close()
    return xrefs, unique_images, duplicates
