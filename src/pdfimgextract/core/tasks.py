import fitz

from pdfimgextract.models.types import ExtractTask, Args
from pdfimgextract.utils.filesystem import load_existing_files
from pdfimgextract.utils.dedup import scan_pdf_images
from pdfimgextract.constants.colors import ENDC, YELLOW


def _build_extract_tasks(xrefs: list[int], args: Args) -> list[ExtractTask]:
    """
    Build extraction tasks from image xrefs.

    Respects overwrite flag by skipping existing files.
    """

    # Preload existing files (skip check if overwrite is enabled)
    existing_files: set[str] = (
        load_existing_files(args.out_dir) if not args.overwrite else set()
    )

    # Zero-padding size for filenames (001, 002, ...)
    digits: int = len(str(len(xrefs))) if xrefs else 1

    tasks: list[ExtractTask] = []
    skipped: int = 0

    # Open PDF once to read image metadata
    with fitz.open(args.pdf_path) as pdf:
        for index, xref in enumerate(xrefs, start=1):
            img_info = pdf.xref_object(xref, compressed=True)

            # Normalize to bytes
            if isinstance(img_info, str):
                img_info = img_info.encode()

            # Determine image format from PDF filters
            if b"/DCTDecode" in img_info:
                ext = "jpg"
            elif b"/JPXDecode" in img_info:
                ext = "jp2"
            elif b"/FlateDecode" in img_info:
                ext = "png"
            else:
                ext = "png"

            stem: str = str(index).zfill(digits)
            filename: str = f"{stem}.{ext}"

            # Skip existing files if overwrite is disabled
            if not args.overwrite and filename in existing_files:
                skipped += 1
                continue

            tasks.append(
                ExtractTask(
                    xref=xref,
                    filename=filename,
                    out_dir=args.out_dir,
                )
            )

    # Notify skipped files
    if skipped:
        print(f"{YELLOW}Existing files found. Use --overwrite to replace them.{ENDC}")
        print(f"{YELLOW}Skipping {skipped} files in output folder{ENDC}")

    return tasks


def build_tasks(args: Args) -> list[ExtractTask]:
    """
    Scan PDF and return extraction tasks for unique images.

    Dedup behavior is controlled by args.dedup.
    """

    # Get unique image xrefs
    with fitz.open(args.pdf_path) as pdf:
        xrefs = scan_pdf_images(pdf, args.dedup)

    return _build_extract_tasks(xrefs, args)
