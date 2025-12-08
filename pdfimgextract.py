from concurrent.futures import ProcessPoolExecutor, as_completed
import os
import sys
import fitz
import argparse

red = '\033[91m'
green = '\033[92m'
endc = '\033[0m'

class Parser(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write(f"{red}Error: {message}{endc}\n\n")
        sys.exit(1)

    def parse_args(self, *args, **kwargs):
        parsed = super().parse_args(*args, **kwargs)

        if not os.path.isfile(parsed.input):
            self.error(f"Input file '{parsed.input}' does not exist or is not a file.")

        return parsed


def get_args():
    parser = Parser(
        description="Inline python script to extract images from PDF files",
        epilog=f"{green}Usage example: pdfimgextract -i file.pdf -o output_folder -p 4{endc}",
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


def extract_images_parallel(pdf_path, out_dir, workers):
    os.makedirs(out_dir, exist_ok=True)

    with fitz.open(pdf_path) as pdf:
        tasks = []
        for page_index, page in enumerate(pdf):
            for img_index, img in enumerate(page.get_images(full=True), start=1):
                xref = img[0]
                tasks.append((pdf_path, xref, out_dir, None))

    total = len(tasks)
    digits = len(str(total))

    for i, t in enumerate(tasks, start=1):
        filename = str(i).zfill(digits)
        tasks[i - 1] = (t[0], t[1], t[2], filename)

    results = []
    with ProcessPoolExecutor(max_workers=workers) as exe:
        futures = [exe.submit(worker_extract, t) for t in tasks]
        for f in as_completed(futures):
            results.append(f.result())

    print(f"{green}{len(results)} imagens extraídas para {out_dir}{endc}")


if __name__ == "__main__":
    args = get_args()
    extract_images_parallel(args.input, args.output, args.parallelism)
