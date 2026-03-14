import os
import fitz
import hashlib

from pdfimgextract.colors import ENDC, YELLOW
from pdfimgextract.datamodels import ExtractTask
from pdfimgextract.progress_bar import (
    create_progress_bar,
    update_scan_stats,
    scanning_complete,
)


def _load_existing_stems(out_dir: str) -> set[str]:
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
    width = img[2]
    height = img[3]
    bpc = img[4]
    colorspace = img[5]

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


def _scan_pdf_images(pdf: fitz.Document) -> tuple[list[int], int, int]:
    """
    Scan the PDF and return a list of unique image xrefs.

    Deduplication is performed using:

    1. xref check (fast)
    2. metadata signature
    3. stream hash (slow but accurate)

    Returns:
        xrefs: list of unique image references
        unique_images: number of accepted images
        duplicates: number of skipped duplicates
    """

    seen_xref: set[int] = set()
    seen_signatures: set[tuple] = set()
    seen_hashes: set[bytes] = set()

    xrefs: list[int] = []

    unique_images = 0
    duplicates = 0

    progress = create_progress_bar(len(pdf), desc="Scanning PDF")

    for page in pdf:

        for img in page.get_images(full=True):

            xref = img[0]

            # Skip if this object was already processed
            if xref in seen_xref:
                duplicates += 1
                continue

            seen_xref.add(xref)

            signature = _image_signature(img)

            img_hash = None

            # If signature already seen, confirm with hash
            if signature in seen_signatures:
                img_hash = _compute_stream_hash(pdf, xref)

                if img_hash and img_hash in seen_hashes:
                    duplicates += 1
                    continue

            # Accept image
            xrefs.append(xref)
            unique_images += 1
            seen_signatures.add(signature)

            if img_hash is None:
                img_hash = _compute_stream_hash(pdf, xref)

            if img_hash:
                seen_hashes.add(img_hash)

        progress.update(1)
        update_scan_stats(progress, unique_images, duplicates)

    scanning_complete(progress)
    progress.close()

    return xrefs, unique_images, duplicates


def _build_extract_tasks(
    xrefs: list[int],
    out_dir: str,
    run_id: str,
    overwrite: bool,
) -> list[ExtractTask]:
    """
    Convert image xrefs into ExtractTask objects.
    """

    existing_stems = _load_existing_stems(out_dir) if not overwrite else set()

    digits = len(str(len(xrefs))) if xrefs else 1

    tasks: list[ExtractTask] = []
    skipped = 0

    for index, xref in enumerate(xrefs, start=1):

        stem = str(index).zfill(digits)

        if not overwrite and stem in existing_stems:
            skipped += 1
            continue

        tasks.append(
            ExtractTask(
                xref=xref,
                stem=stem,
                out_dir=out_dir,
                run_id=run_id,
            )
        )

    if skipped:
        print(
            f"{YELLOW}Overwrite is disabled, if you want to overwrite existing files, use --overwrite flag{ENDC}"
        )
        print(f"{YELLOW}Skipping {skipped} existing files in destination folder{ENDC}")

    return tasks


def build_tasks(
    pdf_path: str,
    out_dir: str,
    run_id: str,
    overwrite: bool,
) -> list[ExtractTask]:
    """
    Scan a PDF and create extraction tasks for unique images.

    The function performs a full scan of the PDF to detect images
    and remove duplicates using multiple levels of checks.

    Deduplication strategy:

    1. Skip repeated xref objects
    2. Compare metadata signatures
    3. Confirm duplicates using a SHA256 hash of the image stream

    After scanning, extraction tasks are generated for each
    unique image.
    """

    with fitz.open(pdf_path) as pdf:
        xrefs, _, _ = _scan_pdf_images(pdf)

    return _build_extract_tasks(
        xrefs=xrefs,
        out_dir=out_dir,
        run_id=run_id,
        overwrite=overwrite,
    )
