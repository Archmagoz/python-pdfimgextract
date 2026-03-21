from __future__ import annotations

from multiprocessing.pool import Pool

from pdfimgextract.datamodels import Args, ExtractResult
from pdfimgextract.worker import init_worker, worker_extract
from pdfimgextract.filesystem import remove_file_safely
from pdfimgextract.commit import finalize_result


def handle_interrupt(pool, progress, stop_event):
    """
    Handle a CTRL-C interruption during pool execution.

    Signals workers to stop via the stop_event, updates the progress bar
    to indicate cancellation, and forcefully terminates the worker pool.
    """
    stop_event.set()

    if progress is not None:
        progress.set_description("Cancelled (CTRL-C)")
        progress.colour = "yellow"
        progress.refresh()

    if pool is not None:
        pool.terminate()
        pool.join()


def run_pool(tasks: list, args: Args, stop_event, progress):
    """
    Execute extraction tasks using a multiprocessing pool.

    This function is responsible only for:
    - creating the worker pool
    - dispatching tasks
    - collecting results
    - handling cancellation/interrupts

    Higher-level error handling and exit codes are managed by the caller.

    Args:
        tasks: Iterable of ExtractTask objects.
        workers: Number of worker processes.
        pdf_path: Path to the source PDF file.
        stop_event: Multiprocessing Event used to signal cancellation.
        progress: tqdm progress bar instance.
        out_dir: Directory where extracted images will be written.

    Returns:
        tuple:
            results (list[ExtractResult]): All processed task results.
            failed (list[ExtractResult]): Tasks that failed (excluding cancellations).
            success_count (int): Number of successful extractions.
            interrupted (bool): True if execution was interrupted by CTRL-C.
    """

    pool: Pool | None = None
    interrupted = False

    # Aggregated execution results
    results: list[ExtractResult] = []
    failed: list[ExtractResult] = []
    success_count = 0

    # Create worker pool with per-process PDF initialization
    pool = Pool(
        processes=args.workers,
        initializer=init_worker,
        initargs=(args.pdf_path, stop_event),
    )

    try:
        # Process results as workers finish tasks (unordered)
        for raw_result in pool.imap_unordered(worker_extract, tasks, chunksize=1):

            # If cancellation was requested, discard temporary output
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
                # Finalize the worker result (move temp file, validate, etc.)
                result, _ = finalize_result(raw_result, out_dir=args.out_dir)

            results.append(result)

            # Track statistics
            if result.ok:
                success_count += 1
            elif not result.cancelled:
                failed.append(result)

            progress.update(1)

        # Graceful shutdown
        pool.close()
        pool.join()

    except KeyboardInterrupt:
        interrupted = True
        handle_interrupt(pool, progress, stop_event)

    return results, failed, success_count, interrupted
