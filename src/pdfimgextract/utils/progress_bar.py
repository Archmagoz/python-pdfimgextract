from tqdm import tqdm


def create_progress_bar(
    total: int | None = None,
    desc: str = "Processing",
    unit: str = "Item",
) -> tqdm:
    """
    Create a standardized tqdm progress bar.

    Centralizes visual configuration to keep all progress bars consistent.
    """

    return tqdm(
        total=total,
        desc=desc,
        colour="green",
        leave=True,
        dynamic_ncols=True,
        unit=f" {unit}",
        smoothing=0.1,
    )


def update_scan_stats(progress: tqdm, unique: int, duplicates: int) -> None:
    """
    Update scan statistics (unique images vs duplicates).
    """

    progress.set_postfix(
        unique=unique,
        dup=duplicates,
    )


def update_extract_stats(progress: tqdm, success: int, failed: int) -> None:
    """
    Update extraction statistics (success vs failure).
    """

    progress.set_postfix(
        ok=success,
        fail=failed,
    )


def scanning_complete(progress: tqdm) -> None:
    """
    Mark scanning phase as complete.
    """

    progress.set_description("Scanning complete")
    progress.refresh()


def finish_progress_bar(progress: tqdm, cancelled: bool = False) -> None:
    """
    Finalize progress bar state (completed or cancelled).
    """

    if cancelled:
        progress.set_description_str("Cancelled (CTRL-C)")
        progress.colour = "yellow"
    else:
        progress.set_description_str("Extraction completed")
        progress.colour = "green"

    progress.refresh()
    progress.close()
