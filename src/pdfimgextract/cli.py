from colorama import init as colorama_init

from pdfimgextract.args import get_args
from pdfimgextract.extract import extract_images_parallel


def main() -> int:
    colorama_init()

    args = get_args()

    return extract_images_parallel(
        pdf_path=args.input,
        out_dir=args.output,
        workers=args.parallelism,
        overwrite=args.overwrite,
        dedup=args.skip_dedup,
    )
