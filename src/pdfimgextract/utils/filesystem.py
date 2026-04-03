import os

from contextlib import suppress


def load_existing_files(output_dir: str) -> set[str]:
    """
    Collect full filenames from the output directory.

    Used to skip already existing files when overwrite is disabled.
    """

    filenames: set[str] = set()

    # Return empty set if directory does not exist
    if not os.path.isdir(output_dir):
        return filenames

    for filename in os.listdir(output_dir):
        if os.path.isfile(os.path.join(output_dir, filename)):
            filenames.add(filename)

    return filenames


def remove_file_safely(path: str | None) -> None:
    """
    Remove a file, ignoring any filesystem errors.

    No-op if path is None or removal fails.
    """

    if not path:
        return

    with suppress(OSError):
        os.remove(path)


def cleanup_stale_temp_files(out_dir: str) -> None:
    """
    Remove leftover temporary files from previous runs.

    Targets files matching: `.pdfimgextract-tmp-*.part`
    """

    # Skip if directory does not exist
    if not os.path.isdir(out_dir):
        return

    for name in os.listdir(out_dir):
        # Match temp files created during extraction
        if name.startswith(".pdfimgextract-tmp-") and name.endswith(".part"):
            remove_file_safely(os.path.join(out_dir, name))
