import fitz
import uuid

from pdfimgextract.dedup import load_existing_stems, scan_pdf_images
from pdfimgextract.datamodels import ExtractTask, Args

from pdfimgextract.colors import ENDC, YELLOW


def _build_extract_tasks(
    xrefs: list[int],
    out_dir: str,
    run_id: str,
    overwrite: bool,
) -> list[ExtractTask]:
    """
    Convert image xrefs into ExtractTask objects.
    """

    existing_stems = load_existing_stems(out_dir) if not overwrite else set()
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
    args: Args,
    run_id: str | None = None,
) -> list[ExtractTask]:
    """
    Scan a PDF and create extraction tasks for unique images.
    """

    run_id = run_id or str(uuid.uuid4())

    with fitz.open(args.pdf_path) as pdf:
        xrefs, _, _ = scan_pdf_images(pdf, args.dedup)

    return _build_extract_tasks(
        xrefs=xrefs,
        out_dir=args.out_dir,
        run_id=run_id,
        overwrite=args.overwrite,
    )
