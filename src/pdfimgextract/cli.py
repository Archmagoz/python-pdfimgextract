from __future__ import annotations

from multiprocessing import Event
from multiprocessing.pool import Pool
from dataclasses import dataclass
from colorama import Fore, Style, init as colorama_init
from tqdm import tqdm
from typing import Protocol
from contextlib import suppress

import argparse
import atexit
import os
import signal
import sys
import uuid

import fitz

# ============================================================
# Terminal colors
# ============================================================

YELLOW = Fore.YELLOW
GREEN = Fore.GREEN
RED = Fore.RED
ENDC = Style.RESET_ALL

# ============================================================
# Standardized exit codes
# ============================================================

EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_BY_USER = 2

# ============================================================
# Worker global state
# ============================================================


class SharedEventProtocol(Protocol):
    def is_set(self) -> bool: ...
    def set(self) -> None: ...


PDF_DOC: fitz.Document | None = None
STOP_EVENT: SharedEventProtocol | None = None

# ============================================================
# Data models
# ============================================================


@dataclass(frozen=True)
class ExtractTask:
    xref: int
    stem: str
    out_dir: str
    run_id: str


@dataclass(frozen=True)
class ExtractResult:
    ok: bool
    cancelled: bool
    xref: int
    stem: str
    ext: str | None
    temp_path: str | None
    error: str | None


# ============================================================
# Argument parsing and validation + custom error reporting
# ============================================================


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

    args.input = args.input or args.input_pos
    args.output = args.output or args.output_pos
    args.parallelism = args.parallelism or args.parallelism_pos or 8

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


# ============================================================
# Temporary file cleanup
# ============================================================


def remove_file_safely(path: str | None) -> None:
    if not path:
        return

    with suppress(OSError):
        os.remove(path)


def cleanup_stale_temp_files(out_dir: str) -> None:
    if not os.path.isdir(out_dir):
        return

    for name in os.listdir(out_dir):
        if name.startswith(".pdfimgextract-tmp-") and name.endswith(".part"):
            remove_file_safely(os.path.join(out_dir, name))


# ============================================================
# Image discovery
# ============================================================


def build_tasks(pdf_path: str, out_dir: str, run_id: str) -> list[ExtractTask]:
    xrefs: list[int] = []
    seen: set[int] = set()

    with fitz.open(pdf_path) as pdf:
        for page in pdf:
            for img in page.get_images(full=True):
                xref = img[0]

                if xref in seen:
                    continue

                seen.add(xref)
                xrefs.append(xref)

    digits = len(str(len(xrefs))) if xrefs else 1

    tasks: list[ExtractTask] = []
    for index, xref in enumerate(xrefs, start=1):
        stem = str(index).zfill(digits)
        tasks.append(
            ExtractTask(
                xref=xref,
                stem=stem,
                out_dir=out_dir,
                run_id=run_id,
            )
        )

    return tasks


# ============================================================
# Worker lifecycle
# ============================================================


def close_worker_pdf() -> None:
    global PDF_DOC
    if PDF_DOC is not None:
        with suppress(Exception):
            PDF_DOC.close()
        PDF_DOC = None


def init_worker(pdf_path: str, stop_event: SharedEventProtocol) -> None:
    global PDF_DOC, STOP_EVENT

    signal.signal(signal.SIGINT, signal.SIG_IGN)

    PDF_DOC = fitz.open(pdf_path)
    STOP_EVENT = stop_event

    atexit.register(close_worker_pdf)


# ============================================================
# Result helpers
# ============================================================


def cancelled_result(task: ExtractTask) -> ExtractResult:
    return ExtractResult(
        ok=False,
        cancelled=True,
        xref=task.xref,
        stem=task.stem,
        ext=None,
        temp_path=None,
        error="cancelled",
    )


def failure_result(task: ExtractTask, error: str) -> ExtractResult:
    return ExtractResult(
        ok=False,
        cancelled=False,
        xref=task.xref,
        stem=task.stem,
        ext=None,
        temp_path=None,
        error=error,
    )


# ============================================================
# Worker extraction
# ============================================================


def worker_extract(task: ExtractTask) -> ExtractResult:
    global PDF_DOC, STOP_EVENT

    temp_path: str | None = None

    try:
        if STOP_EVENT is None:
            raise RuntimeError("Worker stop event is not initialized.")

        if STOP_EVENT.is_set():
            return cancelled_result(task)

        if PDF_DOC is None:
            raise RuntimeError("Worker PDF document is not initialized.")

        base_image = PDF_DOC.extract_image(task.xref)

        image_bytes = base_image.get("image")
        raw_ext = str(base_image.get("ext", "")).strip()

        if not image_bytes:
            raise RuntimeError("PDF image extraction returned empty image data.")

        if not raw_ext:
            raise RuntimeError("PDF image extraction returned empty file extension.")

        ext = raw_ext.lower()

        if STOP_EVENT.is_set():
            return cancelled_result(task)

        temp_path = os.path.join(
            task.out_dir,
            f".pdfimgextract-tmp-{task.run_id}-{task.stem}.{ext}.part",
        )

        with open(temp_path, "wb") as f:
            f.write(image_bytes)

        if STOP_EVENT.is_set():
            remove_file_safely(temp_path)
            return cancelled_result(task)

        return ExtractResult(
            ok=True,
            cancelled=False,
            xref=task.xref,
            stem=task.stem,
            ext=ext,
            temp_path=temp_path,
            error=None,
        )

    except Exception as e:
        remove_file_safely(temp_path)
        return failure_result(task, str(e))


# ============================================================
# Progress bar
# ============================================================


def create_progress_bar(total: int) -> tqdm:
    return tqdm(
        total=total,
        desc="Extracting images",
        colour="green",
        leave=True,
        dynamic_ncols=True,
        unit=" img",
        smoothing=0.1,
    )


def finish_progress_bar(progress: tqdm, cancelled: bool = False) -> None:
    progress.set_description("Cancelled (CTRL-C)" if cancelled else "Completed")
    progress.colour = "yellow" if cancelled else "green"
    progress.refresh()
    progress.close()


# ============================================================
# Final commit of extracted images
# ============================================================


def finalize_result(
    result: ExtractResult,
    out_dir: str,
) -> tuple[ExtractResult, str | None]:
    if not result.ok:
        return result, None

    if result.temp_path is None:
        return (
            ExtractResult(
                ok=False,
                cancelled=False,
                xref=result.xref,
                stem=result.stem,
                ext=result.ext,
                temp_path=None,
                error="Invalid worker result: missing temp_path",
            ),
            None,
        )

    if not result.ext:
        remove_file_safely(result.temp_path)
        return (
            ExtractResult(
                ok=False,
                cancelled=False,
                xref=result.xref,
                stem=result.stem,
                ext=None,
                temp_path=None,
                error="Invalid worker result: missing extension",
            ),
            None,
        )

    final_path = os.path.join(out_dir, f"{result.stem}.{result.ext}")

    try:
        os.replace(result.temp_path, final_path)
    except OSError as e:
        remove_file_safely(result.temp_path)
        return (
            ExtractResult(
                ok=False,
                cancelled=False,
                xref=result.xref,
                stem=result.stem,
                ext=result.ext,
                temp_path=None,
                error=str(e),
            ),
            None,
        )

    return (
        ExtractResult(
            ok=True,
            cancelled=False,
            xref=result.xref,
            stem=result.stem,
            ext=result.ext,
            temp_path=None,
            error=None,
        ),
        final_path,
    )


# ============================================================
# Main execution
# ============================================================


def extract_images_parallel(pdf_path: str, out_dir: str, workers: int) -> int:
    os.makedirs(out_dir, exist_ok=True)

    progress: tqdm | None = None
    pool: Pool | None = None
    interrupted = False
    run_id = uuid.uuid4().hex[:12]

    try:
        cleanup_stale_temp_files(out_dir)

        tasks = build_tasks(pdf_path, out_dir, run_id)
        total = len(tasks)

        if total == 0:
            print(f"{YELLOW}No images found in PDF{ENDC}")
            return EXIT_SUCCESS

        # ============================================================
        # Shared stop signal
        # ============================================================
        #
        # Use multiprocessing.Event directly instead of Manager().Event()
        # to reduce IPC overhead and improve throughput, while preserving
        # the same cancellation semantics used by the workers.
        #
        stop_event = Event()

        results: list[ExtractResult] = []
        failed: list[ExtractResult] = []
        success_count = 0

        progress = create_progress_bar(total)

        try:
            pool = Pool(
                processes=workers,
                initializer=init_worker,
                initargs=(pdf_path, stop_event),
            )

            chunksize = max(1, total // (workers * 8))

            for raw_result in pool.imap_unordered(
                worker_extract, tasks, chunksize=chunksize
            ):
                if stop_event.is_set():
                    if raw_result.temp_path is not None:
                        remove_file_safely(raw_result.temp_path)

                    result = ExtractResult(
                        ok=False,
                        cancelled=True,
                        xref=raw_result.xref,
                        stem=raw_result.stem,
                        ext=raw_result.ext,
                        temp_path=None,
                        error="cancelled",
                    )
                else:
                    result, _ = finalize_result(
                        raw_result,
                        out_dir=out_dir,
                    )

                results.append(result)

                if result.ok:
                    success_count += 1
                elif not result.cancelled:
                    failed.append(result)

                progress.update(1)

            pool.close()
            pool.join()
            pool = None

        except KeyboardInterrupt:
            interrupted = True
            stop_event.set()

            if progress is not None:
                progress.set_description("Cancelled (CTRL-C)")
                progress.colour = "yellow"
                progress.refresh()

            if pool is not None:
                pool.terminate()
                pool.join()
                pool = None

        except Exception:
            stop_event.set()

            if pool is not None:
                pool.terminate()
                pool.join()
                pool = None

            raise

        finally:
            if progress is not None:
                finish_progress_bar(progress, interrupted)
                progress = None

        cleanup_stale_temp_files(out_dir)

        fail_count = len(failed)

        if interrupted:
            remaining = total - len(results)

            print(f"{YELLOW}{success_count} images extracted before interruption{ENDC}")

            if fail_count > 0:
                print(f"{YELLOW}{fail_count} images failed to extract{ENDC}")
                for r in failed:
                    print(
                        f"{YELLOW}- image #{r.stem} "
                        f"(xref={r.xref}): {r.error}{ENDC}"
                    )

            print(f"{YELLOW}{remaining} images were not processed{ENDC}")
            print(f"{YELLOW}Interrupted by user (CTRL-C){ENDC}")
            return EXIT_BY_USER

        print(
            f"{GREEN}{success_count} images successfully extracted to {out_dir}{ENDC}"
        )

        if fail_count > 0:
            print(f"{YELLOW}{fail_count} images failed to extract{ENDC}")
            for r in failed:
                print(f"{YELLOW}- image #{r.stem} " f"(xref={r.xref}): {r.error}{ENDC}")
            return EXIT_FAILURE

        return EXIT_SUCCESS

    except Exception as e:
        if progress is not None:
            with suppress(Exception):
                finish_progress_bar(progress, interrupted)

        if pool is not None:
            with suppress(Exception):
                pool.terminate()
            with suppress(Exception):
                pool.join()

        cleanup_stale_temp_files(out_dir)

        print(f"{RED}Fatal error: {e}{ENDC}", file=sys.stderr)
        return EXIT_FAILURE


# ============================================================
# Entry point
# ============================================================


def main() -> int:
    colorama_init()

    args = get_args()

    return extract_images_parallel(
        pdf_path=args.input,
        out_dir=args.output,
        workers=args.parallelism,
    )
