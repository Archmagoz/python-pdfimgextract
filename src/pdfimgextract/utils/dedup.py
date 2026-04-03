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

    stream: bytes | None = pdf.xref_stream(xref)

    if stream is None:
        return None

    return hashlib.sha256(stream).digest()


def scan_pdf_images(pdf: fitz.Document, dedup: str) -> list[int]:
    """
    Scan all pages and collect unique image xrefs.
    """

    seen_xref: set[int] = set()
    seen_hashes: set[bytes] = set()
    xrefs: list[int] = []
    unique_images: int = 0
    duplicates: int = 0
    total: int = len(pdf)

    progress = create_progress_bar(total, desc="Scanning PDF", unit="page")
    dedup_method = dedup.lower()

    try:
        if dedup_method == "xref":
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

                update_scan_stats(progress, unique_images, duplicates)

        elif dedup_method == "hash":
            for page in pdf:
                imgs: list[tuple] = page.get_images(full=True)
                for img in imgs:
                    xref = img[0]

                    if xref in seen_xref:
                        duplicates += 1
                        continue

                    seen_xref.add(xref)
                    img_hash = _compute_stream_hash(pdf, xref)

                    # Skip invalid or duplicate hashes
                    if img_hash is None:
                        duplicates += 1
                        continue

                    if img_hash in seen_hashes:
                        duplicates += 1
                        continue

                    seen_hashes.add(img_hash)
                    xrefs.append(xref)
                    unique_images += 1

                update_scan_stats(progress, unique_images, duplicates)

    except KeyboardInterrupt:
        if progress is not None:
            with suppress(Exception):
                finish_progress_bar(progress, cancelled=True)

        raise

    if progress is not None:
        scanning_complete(progress)
        progress.close()

    return xrefs
