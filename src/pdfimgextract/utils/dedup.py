import hashlib
import fitz

from contextlib import suppress

from pdfimgextract.utils.progress_bar import (
    create_progress_bar,
    update_scan_stats,
    scanning_complete,
    finish_progress_bar,
)


def _compute_stream_hash(pdf: fitz.Document, xref: int) -> bytes | None:
    """
    Compute a SHA256 hash from the raw image stream.

    Returns None if the stream cannot be accessed.
    """

    stream = pdf.xref_stream(xref)
    if stream is None:
        return None
    return hashlib.sha256(stream).digest()


def scan_pdf_images(pdf: fitz.Document, dedup: str) -> tuple[list[int], int, int]:
    """
    Scan all pages and collect unique image xrefs.

    Deduplication strategies:
    - "xref": skip repeated references (fast)
    - "hash": compare image content (slower, more accurate)

    Returns:
        (xrefs, unique_count, duplicate_count)
    """

    seen_xref: set[int] = set()
    seen_hashes: set[bytes] = set()
    xrefs: list[int] = []
    unique_images: int = 0
    duplicates: int = 0
    total: int = len(pdf)

    progress = create_progress_bar(total, desc="Scanning PDF", unit="page")

    try:
        if dedup.lower() == "xref":
            # Fast path: rely only on PDF xref uniqueness
            for page in pdf:
                imgs: list[tuple] = page.get_images(full=True)
                for img in imgs:
                    xref = img[0]

                    if xref not in seen_xref:
                        seen_xref.add(xref)
                        xrefs.append(xref)
                        unique_images += 1
                    else:
                        duplicates += 1

                progress.update(1)
                update_scan_stats(progress, unique_images, duplicates)

        elif dedup.lower() == "hash":
            # Slower path: detect duplicates by image content
            for page in pdf:
                imgs: list[tuple] = page.get_images(full=True)
                for img in imgs:
                    xref = img[0]

                    # Skip already processed references early
                    if xref in seen_xref:
                        duplicates += 1
                        continue

                    seen_xref.add(xref)
                    img_hash = _compute_stream_hash(pdf, xref)

                    # Skip if identical image content was already seen
                    if img_hash in seen_hashes:
                        duplicates += 1
                        continue

                    if img_hash:
                        seen_hashes.add(img_hash)
                        xrefs.append(xref)
                        unique_images += 1

                progress.update(1)
                update_scan_stats(progress, unique_images, duplicates)

    except KeyboardInterrupt:
        # Ensure progress bar is properly finalized on interruption
        if progress is not None:
            with suppress(Exception):
                finish_progress_bar(progress, cancelled=True)
        raise

    scanning_complete(progress)
    progress.close()

    return xrefs, unique_images, duplicates
