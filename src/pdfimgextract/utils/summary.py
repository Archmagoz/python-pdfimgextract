from pdfimgextract.models.types import ExtractionSummary, PoolResult
from pdfimgextract.constants.colors import YELLOW, GREEN, ENDC


def _print_failed(results):
    """
    Print details for each failed (non-cancelled) extraction.
    """
    for r in results:
        if not r.ok and not r.cancelled:
            print(f"{YELLOW}- image #{r.filename} (xref={r.xref}): {r.error}{ENDC}")


def print_summary(result: PoolResult, total: int, out_dir: str) -> ExtractionSummary:
    """
    Print a summary of the extraction process and return aggregated stats.
    """

    success_count = result.success_count
    fail_count = result.failed_count
    interrupted = result.interrupted
    results = result.results

    if interrupted:
        # Compute how many tasks were never processed
        remaining = total - len(results)

        print(f"{YELLOW}{success_count} images extracted before interruption{ENDC}")

        if fail_count:
            print(f"{YELLOW}{fail_count} images failed{ENDC}")
            _print_failed(results)

        if remaining:
            print(f"{YELLOW}{remaining} images not processed{ENDC}")

        return ExtractionSummary(
            success=success_count,
            failed=fail_count,
            interrupted=True,
        )

    # Normal completion path
    if success_count:
        print(f"{GREEN}{success_count} images extracted to {out_dir}{ENDC}")

    if fail_count:
        print(f"{YELLOW}{fail_count} images failed{ENDC}")
        _print_failed(results)

    return ExtractionSummary(
        success=success_count,
        failed=fail_count,
        interrupted=False,
    )
