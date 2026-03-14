from tqdm import tqdm


def create_progress_bar(total: int | None = None, desc: str = "Processing") -> tqdm:
    """
    Create a standardized tqdm progress bar.
    """

    return tqdm(
        total=total,
        desc=desc,
        colour="green",
        leave=True,
        dynamic_ncols=True,
        unit=" img",
        smoothing=0.1,
    )


def update_scan_stats(progress: tqdm, unique: int, duplicates: int) -> None:
    """
    Update stats displayed next to the scanning progress bar.
    """

    progress.set_postfix(
        unique=unique,
        dup=duplicates,
    )


def scanning_complete(progress: tqdm) -> None:
    """
    Mark the scanning phase as completed.
    """

    progress.set_description("Scanning complete")
    progress.refresh()


def finish_progress_bar(progress: tqdm, cancelled: bool = False) -> None:
    """
    Finalize the progress bar.
    """

    progress.set_description(
        "Cancelled (CTRL-C)" if cancelled else "Extraction completed"
    )
    progress.colour = "yellow" if cancelled else "green"
    progress.refresh()
    progress.close()
