from __future__ import annotations

from multiprocessing import Event
from multiprocessing.pool import Pool
from colorama import init as colorama_init
from tqdm import tqdm
from contextlib import suppress

import os
import sys
import uuid

import fitz

from pdfimgextract.cli import GREEN, YELLOW, RED, ENDC
from .cleanup import cleanup_stale_temp_files, remove_file_safely
from .args import get_args
from .worker import init_worker, worker_extract, ExtractTask, ExtractResult

# Standardized exit codes
EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_BY_USER = 130

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

            # Each worker will work with one image at a time to better reporting of progress and
            # faster cancellation response, at the cost of some parallelism efficiency.
            # This is a deliberate choice to prioritize user experience and responsiveness,
            # especially for large PDFs with many images or big images, so keep chunksize=1.
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
