from __future__ import annotations

from multiprocessing.pool import Pool

from pdfimgextract.core.worker import init_worker, worker_extract
from pdfimgextract.core.commit import finalize_result
from pdfimgextract.models.datamodels import Args, ExtractResult
from pdfimgextract.models.datamodels import PoolResult
from pdfimgextract.utils.filesystem import remove_file_safely


def _handle_interrupt(progress, stop_event):
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


def run_pool(tasks: list, args: Args, stop_event, progress) -> PoolResult:
    """
    Execute extraction tasks using a multiprocessing pool.

    This function is responsible only for:
    - creating the worker pool
    - dispatching tasks
    - collecting results
    - handling cancellation/interrupts
    """

    pool: Pool | None = None
    interrupted: bool = False

    results: list[ExtractResult] = []
    success_count: int = 0
    failed_count: int = 0

    pool = Pool(
        processes=args.workers,
        initializer=init_worker,
        initargs=(args.pdf_path, stop_event),
    )

    try:
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
                result, _ = finalize_result(raw_result, out_dir=args.out_dir)

            results.append(result)

            if result.ok:
                success_count += 1
            elif not result.cancelled:
                failed_count += 1

            if progress is not None:
                progress.update(1)

    except KeyboardInterrupt:
        interrupted = True
        _handle_interrupt(progress, stop_event)

    finally:
        if pool is not None:
            pool.terminate() if interrupted else pool.close()
            pool.join()

    return PoolResult(
        results=results,
        success_count=success_count,
        failed_count=failed_count,
        interrupted=interrupted,
    )
