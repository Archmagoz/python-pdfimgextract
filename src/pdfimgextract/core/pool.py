from __future__ import annotations

from multiprocessing.pool import Pool

from pdfimgextract.core.worker import init_worker, worker_extract
from pdfimgextract.core.commit import finalize_result
from pdfimgextract.models.datamodels import Args, ExtractResult
from pdfimgextract.models.datamodels import PoolResult
from pdfimgextract.utils.filesystem import remove_file_safely


def _handle_interrupt(progress, stop_event):
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


def run_pool(tasks: list, args: Args, stop_event, progress) -> PoolResult:
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

    # Create worker pool with shared initialization context
    pool = Pool(
        processes=args.workers,
        initializer=init_worker,
        initargs=(args.pdf_path, stop_event),
    )

    try:
        # Iterate over results as they complete (unordered for performance)
        for raw_result in pool.imap_unordered(worker_extract, tasks, chunksize=1):

            # If a stop signal was triggered, treat all further results as cancelled
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
                # Finalize result (e.g., move file, validate output)
                result, _ = finalize_result(raw_result, out_dir=args.out_dir)

            results.append(result)

            # Update counters
            if result.ok:
                success_count += 1
            elif not result.cancelled:
                failed_count += 1

            # Advance progress bar if present
            if progress is not None:
                progress.update(1)

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
