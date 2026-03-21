from pdfimgextract.models.datamodels import Args
from pdfimgextract.core.extract import extract_images_parallel as _extract


def extract_images_parallel(
    pdf_path: str,
    out_dir: str,
    *,
    workers: int = 8,
    overwrite: bool = False,
    dedup: str = "xref",
) -> int:
    args = Args(
        pdf_path=pdf_path,
        out_dir=out_dir,
        workers=workers,
        overwrite=overwrite,
        dedup=dedup,
    )

    return _extract(args)
