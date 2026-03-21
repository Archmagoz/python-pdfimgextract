from colorama import init as colorama_init


from pdfimgextract.core.extract import extract_images_parallel
from pdfimgextract.models.datamodels import Args
from pdfimgextract.cli.parser import get_args


def main() -> int:
    colorama_init()

    args: Args = get_args()

    return extract_images_parallel(args)
