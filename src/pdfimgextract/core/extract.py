from __future__ import annotations

from multiprocessing import Event
from contextlib import suppress
from tqdm import tqdm

import os
import sys
import uuid

from pdfimgextract.core.build_tasks import build_tasks
from pdfimgextract.core.pool import run_pool
from pdfimgextract.models.datamodels import Args
from pdfimgextract.utils.progress_bar import create_progress_bar, finish_progress_bar
from pdfimgextract.utils.filesystem import cleanup_stale_temp_files
from pdfimgextract.utils.summary import print_summary
from pdfimgextract.constants.exit_codes import EXIT_SUCCESS, EXIT_FAILURE, EXIT_BY_USER
from pdfimgextract.constants.colors import RED, YELLOW, ENDC


def extract_images_parallel(args: Args) -> int:
    """
    Extract images from a PDF using parallel worker processes.
    Handles KeyboardInterrupt gracefully and ensures cleanup of
    progress bars and temporary files.
    """

    run_id = uuid.uuid4().hex[:12]
    progress: tqdm | None = None
    interrupted = False
    stop_event = Event()

    total: int = 0
    success_count: int = 0
    failed: list = []
    results: list = []

    try:
        # Build the extraction tasks
        tasks = build_tasks(args, run_id)

        total = len(tasks)
        if total == 0:
            print(f"{YELLOW}No images found in PDF{ENDC}")
            return EXIT_SUCCESS

        # Create progress bar
        progress = create_progress_bar(
            total=total, desc="Extracting images", unit="img"
        )

        # Create a folder immediately before starting the extraction
        os.makedirs(args.out_dir, exist_ok=True)

        # Run extraction pool
        results, failed, success_count, interrupted = run_pool(
            tasks, args, stop_event, progress
        )

    except KeyboardInterrupt:
        interrupted = True
        stop_event.set()
        print(f"{YELLOW}Extraction interrupted by user{ENDC}", file=sys.stderr)
        return EXIT_BY_USER

    except Exception as e:
        # Any other fatal exception
        print(f"{RED}Fatal error: {e}{ENDC}", file=sys.stderr)
        return EXIT_FAILURE

    finally:
        # Unified cleanup for all scenarios (success, error, or interrupt)
        if progress is not None:
            with suppress(Exception):
                finish_progress_bar(progress, interrupted)

        cleanup_stale_temp_files(args.out_dir)

    # Final summary and exit logic
    summary = print_summary(
        success_count,
        len(failed),
        failed,
        interrupted,
        results,
        total,
        args.out_dir,
    )

    # Return appropriate exit code
    if summary.interrupted or summary.failed > 0:
        return EXIT_FAILURE

    return EXIT_SUCCESS
