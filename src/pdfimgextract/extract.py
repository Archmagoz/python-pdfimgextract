from __future__ import annotations

from multiprocessing import Event
from multiprocessing.pool import Pool
from contextlib import suppress
from tqdm import tqdm

import os
import sys
import uuid

from .colors import GREEN, YELLOW, RED, ENDC
from .cleanup import cleanup_stale_temp_files, remove_file_safely
from .worker import init_worker, worker_extract, ExtractResult
from .progress_bar import create_progress_bar, finish_progress_bar
from .commit import finalize_result
from .build_tasks import build_tasks


# Standard exit codes:
EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_BY_USER = 130


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


def print_summary(
    success_count, fail_count, failed, interrupted, results, total, out_dir
):
    if interrupted:
        remaining = total - len(results)

        print(f"{YELLOW}{success_count} images extracted before interruption{ENDC}")

        if fail_count > 0:
            print(f"{YELLOW}{fail_count} images failed to extract{ENDC}")
            for r in failed:
                print(f"{YELLOW}- image #{r.stem} (xref={r.xref}): {r.error}{ENDC}")

        print(f"{YELLOW}{remaining} images were not processed{ENDC}")
        print(f"{YELLOW}Interrupted by user (CTRL-C){ENDC}")
        return EXIT_BY_USER

    print(f"{GREEN}{success_count} images successfully extracted to {out_dir}{ENDC}")

    if fail_count > 0:
        print(f"{YELLOW}{fail_count} images failed to extract{ENDC}")
        for r in failed:
            print(f"{YELLOW}- image #{r.stem} (xref={r.xref}): {r.error}{ENDC}")
        return EXIT_FAILURE

    return EXIT_SUCCESS


def extract_images_parallel(pdf_path: str, out_dir: str, workers: int) -> int:
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

    finally:
        if progress is not None:
            finish_progress_bar(progress, interrupted)
