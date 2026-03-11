from tqdm import tqdm


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
