import os

from contextlib import suppress


def load_existing_stems(out_dir: str) -> set[str]:
    """
    Collect existing file stems from the destination folder.
    Used to avoid recreating files when overwrite is disabled.
    """
    stems: set[str] = set()

    if not os.path.isdir(out_dir):
        return stems

    for name in os.listdir(out_dir):
        stem, _ = os.path.splitext(name)
        stems.add(stem)

    return stems


def remove_file_safely(path: str | None) -> None:
    """
    Attempt to remove a file, ignoring filesystem errors.

    If `path` is None or the file cannot be removed (e.g. permission,
    missing file), the error is silently ignored.
    """
    if not path:
        return

    with suppress(OSError):
        os.remove(path)


def cleanup_stale_temp_files(out_dir: str) -> None:
    """
    Remove leftover temporary files created by pdfimgextract.

    Scans the output directory and deletes files matching the
    pattern `.pdfimgextract-tmp-*.part`.
    """
    if not os.path.isdir(out_dir):
        return

    for name in os.listdir(out_dir):
        if name.startswith(".pdfimgextract-tmp-") and name.endswith(".part"):
            remove_file_safely(os.path.join(out_dir, name))
