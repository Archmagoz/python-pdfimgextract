from __future__ import annotations

from multiprocessing.pool import Pool
from dataclasses import replace
from tqdm import tqdm

from pdfimgextract.models.types import (
    Args,
    ExtractResult,
    ExtractTask,
    PoolResult,
    SharedEventProtocol,
)

from pdfimgextract.core.worker import init_worker, worker_extract
from pdfimgextract.core.commit import finalize_result
from pdfimgextract.utils.progress_bar import update_extract_stats
from pdfimgextract.utils.filesystem import remove_file_safely


def _handle_interrupt(progress: tqdm | None, stop_event: SharedEventProtocol) -> None:
    """
    Handle a CTRL+C interruption during pool execution.

    Sets the shared stop_event to notify all workers to halt processing.
    If a progress bar is active, updates its state to reflect cancellation.
    """

    stop_event.set()

    if progress is not None:
        progress.set_description("Cancelled (CTRL-C)")
        progress.colour = "yellow"
        progress.refresh()


def run_pool(
    tasks: list[ExtractTask],
    args: Args,
    stop_event: SharedEventProtocol,
    progress: tqdm | None,
) -> PoolResult:
    """
    Execute extraction tasks using a multiprocessing pool.

    Responsibilities:
    - Initialize the worker pool
    - Dispatch tasks to workers
    - Collect and process results
    - Handle graceful interruption (CTRL+C)

    This function does not perform extraction logic itself; it only
    orchestrates execution and aggregates results.
    """

    pool: Pool | None = None
    interrupted: bool = False

    results: list[ExtractResult] = []
    success_count: int = 0
    failed_count: int = 0

    try:
        # Create worker pool with shared initialization context
        pool = Pool(
            processes=args.workers,
            initializer=init_worker,
            initargs=(args.pdf_path, stop_event),
        )

        # Iterate over results as they complete (unordered for performance)
        for raw_result in pool.imap_unordered(worker_extract, tasks, chunksize=1):

            # If a stop signal was triggered, treat all further results as cancelled
            if stop_event.is_set():
                if raw_result.temp_path is not None:
                    remove_file_safely(raw_result.temp_path)

                result = replace(
                    raw_result,
                    ok=False,
                    cancelled=True,
                    temp_path=None,
                    error="cancelled",
                )
            else:
                # Finalize result (e.g., move file, validate output)
                result = finalize_result(raw_result, out_dir=args.out_dir)

            results.append(result)

            # Update counters
            if result.ok:
                success_count += 1
            elif not result.cancelled:
                failed_count += 1

            # Advance progress bar if present
            if progress is not None:
                update_extract_stats(progress, success_count, failed_count)

    except KeyboardInterrupt:
        # Capture CTRL+C and trigger controlled shutdown
        interrupted = True
        _handle_interrupt(progress, stop_event)

    finally:
        # Ensure pool is properly cleaned up
        if pool is not None:
            pool.terminate() if interrupted else pool.close()
            pool.join()

    return PoolResult(
        results=results,
        success_count=success_count,
        failed_count=failed_count,
        interrupted=interrupted,
    )
