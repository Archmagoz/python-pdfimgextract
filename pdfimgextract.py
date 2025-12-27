from concurrent.futures import ProcessPoolExecutor
import argparse
import fitz
import sys
import os

# Terminal color codes
GREEN = '\033[92m'
RED = '\033[91m'
ENDC = '\033[0m'

# Custom ArgumentParser
class Parser(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write(f"{RED}Error: {message}{ENDC}\n\n")
        sys.exit(1)


# Handle command-line arguments
def get_args():
    parser = Parser(
        description="Inline python script to extract images from PDF files",
        epilog=f"{GREEN}Usage example:\n"
               f"  pdfimgextract input.pdf output_folder 4\n"
               f"  pdfimgextract -i file.pdf -o output_folder -p 4{ENDC}",
        formatter_class=argparse.RawTextHelpFormatter
    )

    # Positional args
    parser.add_argument("input_pos", 
                        nargs="?", 
                        help="input PDF file")
    
    parser.add_argument("output_pos", 
                        nargs="?", 
                        help="output folder")
    
    parser.add_argument("parallelism_pos", 
                        nargs="?", 
                        type=int, 
                        help="parallelism level")

    # Optional flags
    parser.add_argument("-i", "--input", 
                        help="input PDF file")
    
    parser.add_argument("-o", "--output", 
                        help="output folder")
    
    parser.add_argument("-p", "--parallelism", 
                        type=int, 
                        help="parallelism level (default: 4 workers)")

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

    return args


# Worker function
def worker_extract(task):
    pdf_path, xref, out_dir, filename = task

    with fitz.open(pdf_path) as pdf:
        base_image = pdf.extract_image(xref)

    image_bytes = base_image["image"]
    ext = base_image["ext"]

    path = os.path.join(out_dir, f"{filename}.{ext}")

    with open(path, "wb") as f:
        f.write(image_bytes)

    return path


# Main extractor
def extract_images_parallel(pdf_path, out_dir, workers):
    os.makedirs(out_dir, exist_ok=True)

    tasks = []

    with fitz.open(pdf_path) as pdf:
        for page in pdf:
            for img in page.get_images(full=True):
                tasks.append((pdf_path, img[0], out_dir, None))

    total = len(tasks)
    digits = len(str(total))

    for i, t in enumerate(tasks, start=1):
        tasks[i - 1] = (t[0], t[1], t[2], str(i).zfill(digits))

    with ProcessPoolExecutor(max_workers=workers) as exe:
        results = list(exe.map(worker_extract, tasks))

    print(f"{GREEN}{len(results)} imagens extraídas para {out_dir}{ENDC}")


# Entry point
if __name__ == "__main__":
    args = get_args()
    extract_images_parallel(args.input, args.output, args.parallelism)
