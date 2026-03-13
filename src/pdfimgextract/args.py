import argparse
import os
import sys

from pdfimgextract import __version__
from pdfimgextract.colors import RED, ENDC
from pdfimgextract.exit_codes import EXIT_BY_INCORRECT_USAGE


# Custom ArgumentParser to override the error method for better error messages
class Parser(argparse.ArgumentParser):
    def error(self, message: str):
        sys.stderr.write(f"{RED}Error: {message}{ENDC}\n\n")
        sys.exit(EXIT_BY_INCORRECT_USAGE)


def get_args() -> argparse.Namespace:
    """
    Parse and validate CLI arguments.

    Supports both positional and optional flags for input PDF,
    output directory, and parallelism level.

    Positional usage:
        pdfimgextract input.pdf images 8

    Optional usage:
        pdfimgextract -i input.pdf -o images -p 8

    Returns:
        argparse.Namespace: Parsed and validated arguments with:
            - input (str): Path to the input PDF file.
            - output (str): Output directory for extracted images.
            - parallelism (int): Number of worker processes (default: 8).

    Raises:
        SystemExit: If arguments are invalid or required values are missing.
    """
    parser = Parser(
        prog="pdfimgextract",
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

    # Positional arguments
    parser.add_argument("input_pos", nargs="?", help="input PDF file")
    parser.add_argument("output_pos", nargs="?", help="output folder")
    parser.add_argument(
        "parallelism_pos", nargs="?", type=int, help="parallelism level"
    )

    # Optional flags
    parser.add_argument("-i", "--input", help="input PDF file")
    parser.add_argument("-o", "--output", help="output folder")
    parser.add_argument(
        "-p",
        "--parallelism",
        type=int,
        help="parallelism level (default: 8 workers)",
    )

    # Version flag
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="show program's version number and exit",
    )

    args = parser.parse_args()

    # Map positional arguments to their corresponding optional flags if not provided
    args.input = args.input or args.input_pos
    args.output = args.output or args.output_pos
    args.parallelism = (
        args.parallelism
        if args.parallelism is not None
        else args.parallelism_pos if args.parallelism_pos is not None else 8
    )

    # Validate arguments
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
