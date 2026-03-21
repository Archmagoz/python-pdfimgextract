from pdfimgextract.models.datamodels import ExtractionSummary
from pdfimgextract.constants.colors import YELLOW, GREEN, ENDC


def _print_failed(failed):
    """
    Print details for each failed extraction.

    Args:
        failed: Iterable of ExtractResult objects that failed.
    """
    for r in failed:
        print(f"{YELLOW}- image #{r.stem} (xref={r.xref}): {r.error}{ENDC}")


def print_summary(
    success_count,
    fail_count,
    failed,
    interrupted,
    results,
    total,
    out_dir,
) -> ExtractionSummary:
    """
    Print a summary of the extraction process.

    This function reports the number of successful extractions,
    failures, and interruptions, and returns a structured summary
    object. It does not decide exit codes.

    Args:
        success_count: Number of successfully extracted images.
        fail_count: Number of failed extractions.
        failed: List of failed ExtractResult objects.
        interrupted: Whether the process was interrupted (CTRL-C).
        results: List of processed results.
        total: Total number of tasks initially scheduled.
        out_dir: Output directory where images were written.

    Returns:
        ExtractionSummary containing success/failure counts and
        interruption status.
    """

    if interrupted:
        # Images that were never processed due to interruption
        remaining = total - len(results)

        print(f"{YELLOW}{success_count} images extracted before interruption{ENDC}")

        if fail_count:
            print(f"{YELLOW}{fail_count} images failed{ENDC}")
            _print_failed(failed)

        if remaining:
            print(f"{YELLOW}{remaining} images not processed{ENDC}")

        return ExtractionSummary(
            success=success_count,
            failed=fail_count,
            interrupted=True,
        )

    # Normal completion
    if success_count:
        print(f"{GREEN}{success_count} images extracted to {out_dir}{ENDC}")

    if fail_count:
        print(f"{YELLOW}{fail_count} images failed{ENDC}")
        _print_failed(failed)

    return ExtractionSummary(
        success=success_count,
        failed=fail_count,
        interrupted=False,
    )
