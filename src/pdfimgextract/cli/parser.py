import argparse
import os
import sys

from pdfimgextract import __version__
from pdfimgextract.models.datamodels import Args
from pdfimgextract.constants.colors import RED, ENDC
from pdfimgextract.constants.exit_codes import EXIT_BY_INCORRECT_USAGE


class Parser(argparse.ArgumentParser):
    """
    Custom ArgumentParser with improved error output.

    Overrides the default error handler to display concise,
    user-friendly messages and exit with a custom status code.
    """

    def error(self, message: str):
        sys.stderr.write(f"{RED}Error:{ENDC} {message}\n\n")
        sys.exit(EXIT_BY_INCORRECT_USAGE)


def get_args() -> Args:
    """
    Parse, normalize, and validate command-line arguments.

    Supports both positional arguments and optional flags for flexibility.

    Positional usage:
        pdfimgextract input.pdf output_dir
        pdfimgextract input.pdf output_dir 8

    Optional usage:
        pdfimgextract -i input.pdf -o output_dir -p 8

    Returns:
        Args: A validated configuration object containing:
            - pdf_path (str): Path to the input PDF file.
            - out_dir (str): Output directory for extracted images.
            - workers (int): Number of parallel worker processes.
            - dedup (str): Deduplication strategy ("xref" or "hash").
            - overwrite (bool): Whether to overwrite existing files.

    Exits:
        SystemExit: If validation fails or required arguments are missing.
    """

    parser = Parser(
        prog="pdfimgextract",
        formatter_class=argparse.RawTextHelpFormatter,
        description=(
            "Fast and reliable PDF image extraction.\n\n"
            "Extracts embedded images from PDF files using parallel workers\n"
            "with atomic writes to ensure safe and consistent output."
        ),
        epilog=(
            "Examples:\n"
            "  pdfimgextract input.pdf images\n"
            "  pdfimgextract input.pdf images 8\n"
            "  pdfimgextract -i input.pdf -o images -p 8\n"
            "  pdfimgextract -i input.pdf -o images --overwrite\n\n"
        ),
    )

    # Positional arguments (fallback when flags are not used)
    parser.add_argument("input_pos", nargs="?", help="Input PDF file path")
    parser.add_argument("output_pos", nargs="?", help="Output directory")
    parser.add_argument(
        "parallelism_pos",
        nargs="?",
        type=int,
        help="Number of worker processes (default: 8)",
        default=8,
    )

    # Optional arguments
    parser.add_argument(
        "-i",
        "--input",
        help="Path to the input PDF file",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Directory where extracted images will be saved",
    )
    parser.add_argument(
        "-p",
        "--parallelism",
        type=int,
        help="Number of parallel worker processes (default: 8)",
    )

    # Deduplication strategy
    parser.add_argument(
        "-d",
        "--dedup",
        choices=["xref", "hash"],
        default="xref",
        help=(
            "Deduplication method (default: xref)\n"
            "  xref - skip duplicates using PDF references (fast)\n"
            "  hash - compare image content using hashing (slower, more thorough)"
        ),
    )

    # Overwrite
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing files in the output directory",
    )

    # Version
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show program version and exit",
    )

    args = parser.parse_args()

    # Normalize positional arguments into flags
    args.input = args.input or args.input_pos
    args.output = args.output or args.output_pos
    args.parallelism = args.parallelism or args.parallelism_pos

    # Validation
    if not args.input:
        parser.error("Missing input PDF file.")

    if not os.path.isfile(args.input):
        parser.error(f"Input file not found or invalid: '{args.input}'")

    if not args.output:
        parser.error("Missing output directory.")

    if os.path.exists(args.output) and not os.path.isdir(args.output):
        parser.error(f"Output path exists but is not a directory: '{args.output}'")

    if args.parallelism < 1:
        parser.error("Parallelism must be at least 1.")

    return Args(
        pdf_path=args.input,
        out_dir=args.output,
        workers=args.parallelism,
        overwrite=args.overwrite,
        dedup=args.dedup,
    )
