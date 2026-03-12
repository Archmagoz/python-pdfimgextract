import fitz

from .datamodels import ExtractTask


def build_tasks(pdf_path: str, out_dir: str, run_id: str) -> list[ExtractTask]:
    """
    Scan the PDF and create extraction tasks for each unique image.

    The function iterates through all pages of the PDF, collects unique
    image xrefs, and builds a list of ExtractTask objects used later
    by the worker pool.

    Duplicate images are skipped automatically. Output filenames are
    sequentially numbered with zero-padding based on the total number
    of images found.

    Args:
        pdf_path (str): Path to the input PDF file.
        out_dir (str): Directory where extracted images will be written.
        run_id (str): Unique identifier for the current extraction run.

    Returns:
        list[ExtractTask]: List of tasks representing images to extract.
    """
    xrefs: list[int] = []
    seen: set[int] = set()

    # Extract unique image xrefs from the PDF
    with fitz.open(pdf_path) as pdf:
        for page in pdf:
            for img in page.get_images(full=True):
                xref = img[0]

                if xref in seen:
                    continue

                seen.add(xref)
                xrefs.append(xref)

    digits = len(str(len(xrefs))) if xrefs else 1

    # Build tasks for each unique image xref.
    tasks: list[ExtractTask] = []
    for index, xref in enumerate(xrefs, start=1):
        stem = str(index).zfill(digits)
        tasks.append(
            ExtractTask(
                xref=xref,
                stem=stem,
                out_dir=out_dir,
                run_id=run_id,
            )
        )

    return tasks
