from tqdm import tqdm


def create_progress_bar(
    total: int | None = None,
    desc: str = "Processing",
    unit: str = "item",
) -> tqdm:
    """
    Create a standardized tqdm progress bar.

    This function centralizes ALL visual configuration for progress bars
    used in the application so both phases (scan and extraction) always
    look identical.

    Args:
        total:
            Total number of steps to track.

        desc:
            Text displayed before the progress bar.

        unit:
            Unit label displayed next to the counter.
            Examples:
                "page" -> scanning phase
                "img"  -> extraction phase
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
    Update statistics during the PDF scanning phase.

    Displays how many unique images were discovered and how many
    duplicates were skipped.
    """

    progress.set_postfix(
        unique=unique,
        dup=duplicates,
    )


def update_extract_stats(progress: tqdm, success: int, failed: int) -> None:
    """
    Update statistics during the extraction phase.

    Shows live success/failure counters while images are being written.
    """

    progress.set_postfix(
        ok=success,
        fail=failed,
    )


def scanning_complete(progress: tqdm) -> None:
    """
    Mark the scanning phase as completed.

    The progress bar description is updated so the user can clearly
    see that the scan finished before extraction begins.
    """

    progress.set_description("Scanning complete")
    progress.refresh()


def finish_progress_bar(progress: tqdm, cancelled: bool = False) -> None:
    """
    Finalize a progress bar.

    Updates the visual state to indicate completion or interruption.
    """

    if cancelled:
        progress.set_description_str("Cancelled (CTRL-C)")
        progress.colour = "yellow"
    else:
        progress.set_description_str("Extraction completed")
        progress.colour = "green"

    progress.refresh()
    progress.close()
