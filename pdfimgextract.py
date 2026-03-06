from concurrent.futures import ProcessPoolExecutor, as_completed
from colorama import Fore, Style
from tqdm import tqdm

import argparse
import fitz
import sys
import os

# Terminal color codes
ENDC = Style.RESET_ALL
YELLOW = Fore.YELLOW
GREEN = Fore.GREEN
RED = Fore.RED

# Exit codes
EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_BY_USER = 2


# Custom ArgumentParser
class Parser(argparse.ArgumentParser):
    def error(self, message: str):
        sys.stderr.write(f"{RED}Error: {message}{ENDC}\n\n")
        sys.exit(EXIT_FAILURE)


# Handle command-line arguments
def get_args():
    parser = Parser(
        formatter_class=argparse.RawTextHelpFormatter,
        description="Inline python script to extract images from PDF files",
        epilog="Usage example:\n"
        "  pdfimgextract input.pdf output_folder 4\n"
        "  pdfimgextract -i file.pdf -o output_folder -p 4",
    )

    # Positional args
    parser.add_argument("input_pos", nargs="?", help="input PDF file")
    parser.add_argument("output_pos", nargs="?", help="output folder")
    parser.add_argument(
        "parallelism_pos", nargs="?", type=int, help="parallelism level"
    )

    # Optional flags
    parser.add_argument("-i", "--input", help="input PDF file")
    parser.add_argument("-o", "--output", help="output folder")
    parser.add_argument(
        "-p", "--parallelism", type=int, help="parallelism level (default: 4 workers)"
    )

    args = parser.parse_args()

    # Resolve priority: flag > positional
    args.input = args.input or args.input_pos
    args.output = args.output or args.output_pos
    args.parallelism = args.parallelism or args.parallelism_pos or 4

    # Validation
    if not args.input:
        parser.error("Input PDF not specified.")

    if not os.path.isfile(args.input):
        parser.error(f"Input file '{args.input}' does not exist or is not a file.")

    if not args.output:
        parser.error("Output folder not specified.")

    if args.parallelism < 1:
        parser.error("Parallelism level should be >= 1")

    return args


def ext_fix(ext: str) -> str:
    match ext.lower():
        case "jpx" | "jpeg" | "jpeg2000":
            return "jpg"
        case _:
            return ext.lower()


# Worker function
def worker_extract(task):
    pdf_path, xref, out_dir, filename = task

    try:
        with fitz.open(pdf_path) as pdf:
            base_image = pdf.extract_image(xref)

        image_bytes = base_image["image"]
        ext = ext_fix(base_image["ext"])

        path = os.path.join(out_dir, f"{filename}.{ext}")

        with open(path, "wb") as f:
            f.write(image_bytes)

        return {
            "ok": True,
            "path": path,
            "filename": filename,
            "xref": xref,
            "error": None,
        }

    except Exception as e:
        return {
            "ok": False,
            "path": None,
            "filename": filename,
            "xref": xref,
            "error": str(e),
        }


# task manager
def extract_images_parallel(pdf_path: str, out_dir: str, workers: int) -> int:
    os.makedirs(out_dir, exist_ok=True)

    tasks = []

    with fitz.open(pdf_path) as pdf:
        seen: set[int] = set()

        for page in pdf:
            for img in page.get_images(full=True):
                xref = img[0]

                if xref in seen:
                    continue

                seen.add(xref)
                tasks.append((pdf_path, xref, out_dir, None))

    total = len(tasks)
    digits = len(str(total)) if total > 0 else 1

    for i, t in enumerate(tasks, start=1):
        tasks[i - 1] = (t[0], t[1], t[2], str(i).zfill(digits))

    results = []
    failed = []
    interrupted = False

    with ProcessPoolExecutor(max_workers=workers) as exe:
        futures = [exe.submit(worker_extract, t) for t in tasks]

        try:
            for future in tqdm(
                as_completed(futures),
                total=len(futures),
                colour="green",
                desc="Extracting images",
            ):
                result = future.result()

                results.append(result)

                if not result["ok"]:
                    failed.append(result)

        except KeyboardInterrupt:
            interrupted = True
            print(f"\n{YELLOW}Interrupted by user (CTRL-C){ENDC}")

            for f in futures:
                f.cancel()

            exe.shutdown(wait=False, cancel_futures=True)

    success_count = sum(1 for r in results if r["ok"])
    fail_count = len(failed)

    print(f"{GREEN}{success_count} images successfully extracted to {out_dir}{ENDC}")

    if fail_count > 0:
        print(f"{YELLOW}{fail_count} images failed to extract{ENDC}")

        for r in failed:
            print(
                f"{YELLOW}- image #{r['filename']} (xref={r['xref']}): {r['error']}{ENDC}"
            )

    if interrupted:
        remaining = total - len(results)
        print(f"{YELLOW}{remaining} images were not processed{ENDC}")
        return EXIT_BY_USER

    return EXIT_SUCCESS


# Entry point
def main():
    args = get_args()

    return extract_images_parallel(args.input, args.output, args.parallelism)


if __name__ == "__main__":
    sys.exit(main())
