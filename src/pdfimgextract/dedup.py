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


def _compute_stream_hash(pdf: fitz.Document, xref: int) -> bytes | None:
    """
    Compute a SHA256 hash from the raw image stream.
    Returns None if the stream cannot be read.
    """
    stream = pdf.xref_stream(xref)
    if stream is None:
        return None
    return hashlib.sha256(stream).digest()


def scan_pdf_images(pdf: fitz.Document, dedup: str) -> tuple[list[int], int, int]:
    seen_xref: set[int] = set()
    seen_hashes: set[bytes] = set()

    xrefs: list[int] = []

    unique_images = 0
    duplicates = 0

    progress = create_progress_bar(total=len(pdf), desc="Scanning PDF", unit="page")

    try:
        if dedup.lower() == "xref":
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
            for page in pdf:
                imgs: list[tuple] = page.get_images(full=True)
                for img in imgs:
                    xref = img[0]

                    if xref in seen_xref:
                        duplicates += 1
                        continue

                    seen_xref.add(xref)
                    img_hash = _compute_stream_hash(pdf, xref)

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
        if progress is not None:
            with suppress(Exception):
                finish_progress_bar(progress, cancelled=True)
        raise

    scanning_complete(progress)
    progress.close()
    return xrefs, unique_images, duplicates
