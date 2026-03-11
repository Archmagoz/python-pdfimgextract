import fitz

from .datamodels import ExtractTask


def build_tasks(pdf_path: str, out_dir: str, run_id: str) -> list[ExtractTask]:
    xrefs: list[int] = []
    seen: set[int] = set()

    with fitz.open(pdf_path) as pdf:
        for page in pdf:
            for img in page.get_images(full=True):
                xref = img[0]

                if xref in seen:
                    continue

                seen.add(xref)
                xrefs.append(xref)

    digits = len(str(len(xrefs))) if xrefs else 1

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
