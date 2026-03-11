import argparse
import os

import sys

from pdfimgextract.cli import RED, ENDC
from .cli import EXIT_FAILURE


class Parser(argparse.ArgumentParser):
    def error(self, message: str):
        sys.stderr.write(f"{RED}Error: {message}{ENDC}\n\n")
        sys.exit(EXIT_FAILURE)


def get_args() -> argparse.Namespace:
    parser = Parser(
        formatter_class=argparse.RawTextHelpFormatter,
        description=(
            "Extract images from a PDF file quickly and efficiently.\n"
            "Images are extracted in parallel and saved with atomic writes\n"
            "to ensure safe and reliable output even if interrupted."
        ),
        epilog=(
            "Examples:\n"
            "  pdfimgextract input.pdf images\n"
            "  pdfimgextract input.pdf images 8\n"
            "  pdfimgextract -i input.pdf -o images -p 8\n\n"
            "Notes:\n"
            "  - Duplicate images in the PDF are automatically skipped.\n"
            "  - Extraction runs in parallel for maximum performance.\n"
            "  - Default parallelism: 8 processes."
        ),
    )

    parser.add_argument("input_pos", nargs="?", help="input PDF file")
    parser.add_argument("output_pos", nargs="?", help="output folder")
    parser.add_argument(
        "parallelism_pos", nargs="?", type=int, help="parallelism level"
    )

    parser.add_argument("-i", "--input", help="input PDF file")
    parser.add_argument("-o", "--output", help="output folder")
    parser.add_argument(
        "-p",
        "--parallelism",
        type=int,
        help="parallelism level (default: 8 workers)",
    )

    args = parser.parse_args()

    # Validate and normalize arguments, giving precedence to explicit flags over positional ones
    args.input = args.input or args.input_pos
    args.output = args.output or args.output_pos
    args.parallelism = (
        args.parallelism
        if args.parallelism is not None
        else args.parallelism_pos if args.parallelism_pos is not None else 8
    )

    if not args.input:
        parser.error("Input PDF not specified.")

    if not os.path.isfile(args.input):
        parser.error(f"Input file '{args.input}' does not exist or is not a file.")

    if not args.output:
        parser.error("Output folder not specified.")

    if os.path.exists(args.output) and not os.path.isdir(args.output):
        parser.error(f"Output path '{args.output}' exists and is not a directory.")

    if args.parallelism < 1:
        parser.error("Parallelism level should be >= 1")

    return args
