from __future__ import annotations

from multiprocessing import Event
from multiprocessing.pool import Pool
from contextlib import suppress
from tqdm import tqdm

import os
import sys
import uuid

from .cleanup import cleanup_stale_temp_files, remove_file_safely
from .worker import init_worker, worker_extract, ExtractResult
from .progress_bar import create_progress_bar, finish_progress_bar
from .commit import finalize_result
from .build_tasks import build_tasks
from .summary import print_summary

from pdfimgextract.exit_codes import EXIT_SUCCESS, EXIT_FAILURE
from pdfimgextract.colors import RED, YELLOW, ENDC


# Guarantee cleanup of worker resources on interrupt (e.g. CTRL-C)
def handle_interrupt(pool, progress, stop_event):
    stop_event.set()

    if progress is not None:
        progress.set_description("Cancelled (CTRL-C)")
        progress.colour = "yellow"
        progress.refresh()

    if pool is not None:
        pool.terminate()
        pool.join()


def run_pool(tasks, workers, pdf_path, stop_event, progress, out_dir):
    """
    Run worker pool and process extraction tasks.

    Handles progress updates, cancellation, and cleanup of temp files.

    Returns:
        results
        failed
        success_count
        interrupted
    """
    pool: Pool | None = None
    interrupted = False

    results: list[ExtractResult] = []
    failed: list[ExtractResult] = []
    success_count = 0

    try:
        pool = Pool(
            processes=workers,
            initializer=init_worker,
            initargs=(pdf_path, stop_event),
        )

        # Chunksize of 1 to get results as soon as each task is done, which
        # allows better progress tracking and faster interruption response.
        # The overhead of more frequent inter-process communication is negligible.
        for raw_result in pool.imap_unordered(worker_extract, tasks, chunksize=1):
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
                result, _ = finalize_result(raw_result, out_dir=out_dir)

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
        handle_interrupt(pool, progress, stop_event)
        pool = None

    except Exception:
        stop_event.set()

        if pool is not None:
            pool.terminate()
            pool.join()
            pool = None

        raise

    return results, failed, success_count, interrupted


def extract_images_parallel(pdf_path: str, out_dir: str, workers: int) -> int:
    """
    Extract images from a PDF using parallel worker processes.

    This function orchestrates the full extraction pipeline:
    - Cleans up stale temporary files
    - Scans the PDF and builds extraction tasks
    - Executes the worker pool in parallel
    - Updates the progress bar
    - Finalizes extracted images
    - Prints a summary of the results

    Extraction is designed to be safe and interruptible. If the process
    is interrupted (e.g. CTRL-C) or an error occurs, temporary files are
    cleaned up before exiting.

    Args:
        pdf_path (str): Path to the input PDF file.
        out_dir (str): Directory where extracted images will be saved.
        workers (int): Number of worker processes used for parallel extraction.

    Returns:
        int: Exit code indicating success or failure.
    """
    os.makedirs(out_dir, exist_ok=True)

    progress: tqdm | None = None
    interrupted = False
    run_id = uuid.uuid4().hex[:12]

    try:
        cleanup_stale_temp_files(out_dir)

        tasks = build_tasks(pdf_path, out_dir, run_id)
        total = len(tasks)

        if total == 0:
            print(f"{YELLOW}No images found in PDF{ENDC}")
            return EXIT_SUCCESS

        stop_event = Event()

        progress = create_progress_bar(total)

        results, failed, success_count, interrupted = run_pool(
            tasks,
            workers,
            pdf_path,
            stop_event,
            progress,
            out_dir,
        )

        finish_progress_bar(progress, interrupted)

        cleanup_stale_temp_files(out_dir)

        return print_summary(
            success_count,
            len(failed),
            failed,
            interrupted,
            results,
            total,
            out_dir,
        )

    except Exception as e:
        if progress is not None:
            with suppress(Exception):
                finish_progress_bar(progress, interrupted)

        cleanup_stale_temp_files(out_dir)

        print(f"{RED}Fatal error: {e}{ENDC}", file=sys.stderr)
        return EXIT_FAILURE
