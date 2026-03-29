import fitz

from pdfimgextract.models.types import ExtractTask, Args
from pdfimgextract.utils.filesystem import load_existing_stems
from pdfimgextract.utils.dedup import scan_pdf_images
from pdfimgextract.constants.colors import ENDC, YELLOW


def _build_extract_tasks(xrefs: list[int], args: Args) -> list[ExtractTask]:
    """
    Convert image xrefs into ExtractTask objects, respecting overwrite rules.
    """

    # Load existing output stems to avoid duplicates when overwrite is disabled
    existing_stems = load_existing_stems(args.out_dir) if not args.overwrite else set()

    # Determine zero-padding width based on total number of images
    digits: int = len(str(len(xrefs))) if xrefs else 1

    tasks: list[ExtractTask] = []
    skipped: int = 0

    for index, xref in enumerate(xrefs, start=1):
        stem = str(index).zfill(digits)

        # Skip already existing files when overwrite is disabled
        if not args.overwrite and stem in existing_stems:
            skipped += 1
            continue

        tasks.append(
            ExtractTask(
                xref=xref,
                stem=stem,
                out_dir=args.out_dir,
            )
        )

    # Inform user if files were skipped
    if skipped:
        print(f"{YELLOW}Existing files found. Use --overwrite to overwrite them.{ENDC}")
        print(f"{YELLOW}Skipping {skipped} existing files in destination folder{ENDC}")

    return tasks


def build_tasks(args: Args) -> list[ExtractTask]:
    """
    Scan the PDF and generate extraction tasks for unique images.
    """

    # Extract unique image references according to the selected dedup strategy
    with fitz.open(args.pdf_path) as pdf:
        xrefs = scan_pdf_images(pdf, args.dedup)

    return _build_extract_tasks(xrefs=xrefs, args=args)
