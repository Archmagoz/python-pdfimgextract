from concurrent.futures import ProcessPoolExecutor, as_completed
import argparse
import fitz
import sys
import os

# Terminal color codes
GREEN = '\033[92m'
RED = '\033[91m'
ENDC = '\033[0m'

# Override ArgumentParser to customize error handling
class Parser(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write(f"{RED}Error: {message}{ENDC}\n\n")
        sys.exit(1)

    def parse_args(self, *args, **kwargs):
        parsed = super().parse_args(*args, **kwargs)

        if not os.path.isfile(parsed.input):
            self.error(f"Input file '{parsed.input}' does not exist or is not a file.")

        return parsed


# Handle command-line arguments
def get_args():
    parser = Parser(
        description="Inline python script to extract images from PDF files",
        epilog=f"{GREEN}Usage example: pdfimgextract -i file.pdf -o output_folder -p 4{ENDC}",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    parser.add_argument("-i", "--input", 
                        required=True, 
                        help="input PDF file")
    
    parser.add_argument("-o", "--output", 
                        required=True, 
                        help="output folder for extracted images")
    
    parser.add_argument("-p", "--parallelism", 
                        required=False, 
                        type=int, 
                        default=4, 
                        help="parallelism level (default: 4 workers)")
    
    return parser.parse_args()


# Worker function to extract a single image
def worker_extract(task):
    pdf_path, xref, out_dir, filename = task
    
    with fitz.open(pdf_path) as pdf:
        base_image = pdf.extract_image(xref)

    ext = base_image["ext"]
    image_bytes = base_image["image"]

    path = os.path.join(out_dir, f"{filename}.{ext}")

    with open(path, "wb") as f:
        f.write(image_bytes)

    return path


# Main function to extract images in parallel
def extract_images_parallel(pdf_path, out_dir, workers):
    os.makedirs(out_dir, exist_ok=True)

    results = []
    tasks = []

    with fitz.open(pdf_path) as pdf:
        for page_index, page in enumerate(pdf):
            for img_index, img in enumerate(page.get_images(full=True), start=1):
                xref = img[0]
                tasks.append((pdf_path, xref, out_dir, None))

    total = len(tasks)
    digits = len(str(total))

    for i, t in enumerate(tasks, start=1):
        filename = str(i).zfill(digits)
        tasks[i - 1] = (t[0], t[1], t[2], filename)
    
    with ProcessPoolExecutor(max_workers=workers) as exe:
        futures = [exe.submit(worker_extract, t) for t in tasks]
        for f in as_completed(futures):
            results.append(f.result())

    print(f"{GREEN}{len(results)} imagens extraídas para {out_dir}{ENDC}")


# Entry point
if __name__ == "__main__":
    args = get_args()
    extract_images_parallel(args.input, args.output, args.parallelism)
