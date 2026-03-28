from __future__ import annotations
from multiprocessing import Event
from contextlib import suppress
from tqdm import tqdm

import os
import sys

from pdfimgextract.models.types import Args, PoolResult, SharedEventProtocol
from pdfimgextract.core.tasks import build_tasks
from pdfimgextract.core.pool import run_pool
from pdfimgextract.utils.progress_bar import create_progress_bar, finish_progress_bar
from pdfimgextract.utils.filesystem import cleanup_stale_temp_files
from pdfimgextract.utils.summary import print_summary
from pdfimgextract.constants.colors import RED, YELLOW, ENDC
from pdfimgextract.constants.exit_codes import EXIT_SUCCESS, EXIT_FAILURE, EXIT_BY_USER


def extract_images_parallel(args: Args) -> int:
    """
    This function coordinates the full extraction workflow:
    - builds extraction tasks
    - initializes progress reporting
    - executes workers via a multiprocessing pool
    - handles interruptions and fatal errors
    - performs cleanup of temporary files
    - prints a final execution summary

    Returns:
    - EXIT_SUCCESS: completed without failures
    - EXIT_FAILURE: completed with errors or failed tasks
    - EXIT_BY_USER: interrupted via CTRL-C
    """

    progress: tqdm | None = None
    results: PoolResult | None = None
    stop_event: SharedEventProtocol = Event()

    try:
        # Build extraction tasks (one per image)
        tasks = build_tasks(args)
        total = len(tasks)
        if total == 0:
            print(f"{YELLOW}No images found in PDF{ENDC}")
            return EXIT_SUCCESS

        # Initialize progress bar only after confirming work exists
        progress = create_progress_bar(total, desc="Extracting images", unit="img")

        # Ensure output directory exists before starting workers
        os.makedirs(args.out_dir, exist_ok=True)

        # Execute tasks in parallel
        results = run_pool(tasks, args, stop_event, progress)

    except KeyboardInterrupt:
        stop_event.set()

        print(f"{YELLOW}Extraction interrupted by user{ENDC}", file=sys.stderr)
        return EXIT_BY_USER

    except Exception as e:
        print(
            f"{RED}Fatal error: {type(e).__name__}: {e}{ENDC}",
            file=sys.stderr,
        )
        return EXIT_FAILURE

    finally:
        # Always finalize progress bar safely
        if progress is not None:
            with suppress(Exception):
                is_interrupted = results.interrupted if results else False
                finish_progress_bar(progress, is_interrupted)

        # Cleanup any temporary files left behind
        cleanup_stale_temp_files(args.out_dir)

    # If execution failed before producing results, treat as failure
    if results is None:
        return EXIT_FAILURE

    # Print summary based on collected results
    summary = print_summary(results, total, args.out_dir)

    # Non-zero failures or interruption are considered unsuccessful runs
    if summary.interrupted or summary.failed > 0:
        return EXIT_FAILURE

    return EXIT_SUCCESS
