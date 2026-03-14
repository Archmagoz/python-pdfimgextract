from __future__ import annotations

from multiprocessing import Event
from contextlib import suppress
from tqdm import tqdm

import os
import sys
import uuid

from pdfimgextract.cleanup import cleanup_stale_temp_files
from pdfimgextract.progress_bar import create_progress_bar, finish_progress_bar
from pdfimgextract.build_tasks import build_tasks
from pdfimgextract.summary import print_summary
from pdfimgextract.pool import run_pool
from pdfimgextract.exit_codes import EXIT_SUCCESS, EXIT_FAILURE
from pdfimgextract.colors import RED, YELLOW, ENDC


def extract_images_parallel(
    pdf_path: str, out_dir: str, workers: int, overwrite: bool
) -> int:
    """
    Extract images from a PDF using parallel worker processes.
    """

    os.makedirs(out_dir, exist_ok=True)

    progress: tqdm | None = None
    interrupted = False
    run_id = uuid.uuid4().hex[:12]

    try:
        tasks = build_tasks(pdf_path, out_dir, run_id, overwrite)
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

        summary = print_summary(
            success_count,
            len(failed),
            failed,
            interrupted,
            results,
            total,
            out_dir,
        )

        if summary.interrupted:
            return EXIT_FAILURE

        if summary.failed > 0:
            return EXIT_FAILURE

        return EXIT_SUCCESS

    except KeyboardInterrupt:

        interrupted = True

        if progress is not None:
            with suppress(Exception):
                finish_progress_bar(progress, interrupted)

        cleanup_stale_temp_files(out_dir)

        print(f"{YELLOW}Extraction interrupted by user{ENDC}", file=sys.stderr)

        return EXIT_FAILURE

    except Exception as e:

        if progress is not None:
            with suppress(Exception):
                finish_progress_bar(progress, interrupted)

        cleanup_stale_temp_files(out_dir)

        print(f"{RED}Fatal error: {e}{ENDC}", file=sys.stderr)

        return EXIT_FAILURE
