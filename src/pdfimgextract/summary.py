from pdfimgextract.exit_codes import EXIT_SUCCESS, EXIT_FAILURE, EXIT_BY_USER
from pdfimgextract.colors import YELLOW, GREEN, ENDC


def _print_failed(failed):
    """Print details for failed image extractions."""
    for r in failed:
        print(f"{YELLOW}- image #{r.stem} (xref={r.xref}): {r.error}{ENDC}")


def print_summary(
    success_count, fail_count, failed, interrupted, results, total, out_dir
):
    if interrupted:
        remaining = total - len(results)

        print(f"{YELLOW}{success_count} images extracted before interruption{ENDC}")

        if fail_count > 0:
            print(f"{YELLOW}{fail_count} images failed to extract{ENDC}")
            _print_failed(failed)

        print(f"{YELLOW}{remaining} images were not processed{ENDC}")
        print(f"{YELLOW}Interrupted by user (CTRL-C){ENDC}")

        return EXIT_BY_USER

    print(f"{GREEN}{success_count} images successfully extracted to {out_dir}{ENDC}")

    if fail_count > 0:
        print(f"{YELLOW}{fail_count} images failed to extract{ENDC}")
        _print_failed(failed)
        return EXIT_FAILURE

    return EXIT_SUCCESS
